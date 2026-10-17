"""Regression tests for the 2026-10-08 audit: clean mode must not be exploitable, production must stay clean."""
from __future__ import annotations

import hashlib
import hmac
import json
import time

from app.config import Settings, production_problems, settings


def _login(client, username="admin", password="Admin-2026!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


# --- production guard -----------------------------------------------------------------------------------------

def test_production_refuses_default_secrets_and_stand_modes():
    cfg = Settings(ENVIRONMENT="production", _env_file=None)
    problems = production_problems(cfg)
    assert any("SECRET_KEY" in p for p in problems)
    assert any("PAYMENT_WEBHOOK_SECRET" in p for p in problems)
    assert any("STAND_CONTROL_ENABLED" in p for p in problems)
    ok = Settings(ENVIRONMENT="production", SECRET_KEY="x" * 40, PAYMENT_WEBHOOK_SECRET="y" * 40, STAND_CONTROL_ENABLED=False, _env_file=None)
    assert production_problems(ok) == []
    bad_mode = Settings(ENVIRONMENT="production", SECRET_KEY="x" * 40, PAYMENT_WEBHOOK_SECRET="y" * 40, STAND_CONTROL_ENABLED=False, CRM_MODE="vuln", _env_file=None)
    assert production_problems(bad_mode) == ["CRM_MODE must be clean in production"]


def test_stand_cannot_be_switched_in_production(client, monkeypatch):
    _login(client)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    r = client.patch("/api/stand", json={"crm_mode": "vuln", "VULN_SQLI_SEARCH": True})
    assert r.status_code == 403
    assert settings.CRM_MODE == "clean" and settings.VULN_SQLI_SEARCH is False


def test_stand_patch_replaces_flags_instead_of_accumulating(client):
    _login(client)
    r = client.patch("/api/stand", json={"crm_mode": "experiment", "FAULT_POOL_EXHAUSTED": True})
    assert r.status_code == 200 and settings.FAULT_POOL_EXHAUSTED is True
    r = client.patch("/api/stand", json={"crm_mode": "experiment", "FAULT_TAX_TIMEOUT": True})
    assert r.status_code == 200
    assert settings.FAULT_TAX_TIMEOUT is True and settings.FAULT_POOL_EXHAUSTED is False


def test_public_endpoints_do_not_reveal_the_stand_mode(client):
    settings.CRM_MODE = "vuln"
    assert "crm_mode" not in client.get("/api/stand/public").json()
    _login(client, "viewer", "Viewer-2026!")
    assert client.get("/api/stand").status_code == 403


# --- payments -----------------------------------------------------------------------------------------------

def _signed(body: dict) -> tuple[bytes, dict]:
    raw = json.dumps(body).encode()
    ts = str(int(time.time()))
    sig = hmac.new(settings.PAYMENT_WEBHOOK_SECRET.encode(), raw + ts.encode(), hashlib.sha256).hexdigest()
    return raw, {"X-Signature": sig, "X-Timestamp": ts, "Content-Type": "application/json"}


def _contract(client) -> dict:
    _login(client)
    customers = client.get("/api/customers").json()["items"]
    courses = client.get("/api/courses").json()
    enr = client.post("/api/enrollments", json={"client_id": customers[0]["id"], "course_id": courses[0]["id"], "discount_pct": 0}).json()
    return client.post("/api/contracts", json={"client_id": customers[0]["id"], "number": "BA-SEC-1", "enrollment_ids": [enr[0]["id"]], "discount_pct": 0}).json()


def test_webhook_rejects_negative_or_oversized_amounts(client, db_session):
    contract = _contract(client)
    raw, headers = _signed({"contract_id": contract["id"], "amount_kzt": -5, "external_id": "neg-1"})
    assert client.post("/api/payments/webhook", content=raw, headers=headers).status_code == 400
    raw, headers = _signed({"contract_id": contract["id"], "amount_kzt": 10_000_000, "external_id": "big-1"})
    assert client.post("/api/payments/webhook", content=raw, headers=headers).status_code == 400
    raw, headers = _signed({"contract_id": contract["id"], "amount_kzt": 1000, "external_id": "ok-1", "card_token": "tok_secret"})
    r = client.post("/api/payments/webhook", content=raw, headers=headers)
    assert r.status_code == 200
    from app.models import Payment

    assert db_session.query(Payment).filter_by(external_id="ok-1").one().card_token is None


# --- IDOR in clean mode ----------------------------------------------------------------------------------------

def test_manager_cannot_see_another_managers_contract(client, db_session):
    from app.auth import hash_password
    from app.models import User, UserRole

    contract = _contract(client)  # created by admin for a client owned by "manager"
    db_session.add(User(username="other", email="other@example.com", password_hash=hash_password("Other-2026!"), role=UserRole.manager, is_active=True, max_discount_pct=15))
    db_session.commit()
    _login(client, "other", "Other-2026!")
    cid = contract["id"]
    assert client.get(f"/api/contracts/{cid}/installments").status_code == 404
    assert client.get(f"/api/contracts/{cid}/payments").status_code == 404
    assert client.get(f"/api/contracts/{cid}/export/1c").status_code == 404
    assert client.post(f"/api/contracts/{cid}/installments", json={"months": 3}).status_code == 404
    assert client.get("/api/customers").json()["total"] == 0
    assert client.get("/api/customers/search", params={"name": "Айгуль Тестова"}).json() == []


def test_installment_schedule_is_built_once(client):
    contract = _contract(client)
    assert client.post(f"/api/contracts/{contract['id']}/installments", json={"months": 3}).status_code == 200
    assert client.post(f"/api/contracts/{contract['id']}/installments", json={"months": 3}).status_code == 409
    assert len(client.get(f"/api/contracts/{contract['id']}/installments").json()) == 3


# --- 2026-10-17 audit ---------------------------------------------------------------------------------------

def test_stand_reachable_from_outside_refuses_repository_secrets():
    lab = Settings(ENVIRONMENT="development", BASE_URL="https://crm.csip.dev", CRM_MODE="vuln", _env_file=None)
    assert any("SECRET_KEY" in p for p in production_problems(lab))
    own = Settings(ENVIRONMENT="development", BASE_URL="https://crm.csip.dev", CRM_MODE="vuln", SECRET_KEY="x" * 40,
                   PAYMENT_WEBHOOK_SECRET="y" * 40, _env_file=None)
    assert production_problems(own) == []  # a lab may run vuln mode, but only with its own secrets
    assert production_problems(Settings(ENVIRONMENT="development", _env_file=None)) == []  # localhost stays easy


def test_export_file_of_one_user_is_not_visible_to_another(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXPORT_DIR", str(tmp_path / "exports"))
    _login(client)
    assert client.get("/api/customers/export", params={"fmt": "csv"}).status_code == 200
    assert client.get("/api/customers/export/file", params={"name": "clients.csv"}).status_code == 200
    client.post("/api/auth/logout")
    _login(client, "manager", "Manager-2026!")
    assert client.get("/api/customers/export/file", params={"name": "clients.csv"}).status_code == 404


def test_payments_never_exceed_the_contract_and_bad_json_is_400(client):
    contract = _contract(client)
    total = float(contract["total_kzt"])
    raw, headers = _signed({"contract_id": contract["id"], "amount_kzt": total, "external_id": "full-1"})
    assert client.post("/api/payments/webhook", content=raw, headers=headers).status_code == 200
    raw, headers = _signed({"contract_id": contract["id"], "amount_kzt": 1, "external_id": "over-1"})
    assert client.post("/api/payments/webhook", content=raw, headers=headers).status_code == 400
    raw, headers = _signed({"contract_id": "x"})
    assert client.post("/api/payments/webhook", content=raw, headers=headers).status_code == 400


def test_enrollment_cannot_be_billed_twice(client):
    _login(client)
    customer = client.get("/api/customers").json()["items"][0]
    course = client.get("/api/courses").json()[0]
    enr = client.post("/api/enrollments", json={"client_id": customer["id"], "course_id": course["id"], "discount_pct": 0}).json()[0]
    first = client.post("/api/contracts", json={"client_id": customer["id"], "number": "BA-SEC-2", "enrollment_ids": [enr["id"]], "discount_pct": 0})
    assert first.status_code == 201
    again = client.post("/api/contracts", json={"client_id": customer["id"], "number": "BA-SEC-3", "enrollment_ids": [enr["id"]], "discount_pct": 0})
    assert again.status_code == 409
    empty = client.post("/api/contracts", json={"client_id": customer["id"], "number": "BA-SEC-4", "enrollment_ids": [], "discount_pct": 0})
    assert empty.status_code == 400
