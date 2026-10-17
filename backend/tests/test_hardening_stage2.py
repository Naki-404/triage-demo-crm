"""Stage-2 hardening: login lockout by address, generic 5xx bodies, CSV cells, IIN calendar, one discount, request ids."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app import auth as auth_module
from app.config import settings
from app.iin import InvalidIINError, birth_date, generate_iin, validate_iin
from app.observe import mask_text, valid_request_id
from app.services.customers import csv_safe


def _login(client, username="admin", password="Admin-2026!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


# --- login -----------------------------------------------------------------------------------------------------

def test_unknown_user_and_wrong_password_look_the_same(client):
    a = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    b = client.post("/api/auth/login", json={"username": "manager", "password": "x"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_address_lockout_covers_many_accounts(client):
    for i in range(settings.LOGIN_IP_MAX_FAILURES):
        client.post("/api/auth/login", json={"username": f"user{i}", "password": "x"})
    assert auth_module.ip_locked("testclient")
    r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin-2026!"})
    assert r.status_code == 401
    auth_module.clear_ip_failures("testclient")
    _login(client)


# --- request id ---------------------------------------------------------------------------------------------------

def test_request_id_is_echoed_only_when_well_formed(client):
    ok = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert ok.headers["X-Request-ID"] == "abc-123"
    bad = client.get("/health", headers={"X-Request-ID": "evil\\nX-Injected: 1"})
    assert bad.headers["X-Request-ID"] != "evil\\nX-Injected: 1" and len(bad.headers["X-Request-ID"]) == 32
    assert valid_request_id("a" * 65) is None


def test_mask_text_hides_personal_data():
    masked = mask_text('{"iin": "900101300123", "password": "Secret-1", "email": "a@b.kz", "phone": "+7 701 123 45 67"}')
    assert "900101300123" not in masked and "Secret-1" not in masked and "a@b.kz" not in masked and "123 45 67" not in masked


# --- 5xx bodies are generic ---------------------------------------------------------------------------------------

def test_corrupt_record_returns_generic_500(client, stand_mode):
    stand_mode("experiment", FAULT_CORRUPT_RECORD=True)
    _login(client)
    import random

    from app.iin import generate_iin as gen

    r = client.post("/api/customers", json={"name": "Битая Запись", "iin": gen(random.Random(11)), "phone": "+77010000055"})
    assert r.status_code == 201
    r = client.get(f"/api/customers/{r.json()['id']}")
    assert r.status_code == 500 and r.json() == {"detail": "record error"}


def test_sqli_fault_error_is_not_echoed(client, stand_mode):
    stand_mode("experiment", FAULT_NAME_SEARCH_RAW_SQL=True)
    _login(client)
    r = client.get("/api/customers/search", params={"name": "x' AND 1=CAST('a' AS INT) --"})
    assert r.status_code in (200, 500)
    if r.status_code == 500:
        assert "CAST" not in r.text and r.json()["detail"] == "search failed"


# --- CSV ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["=1+1", "+1", "-1", "@cmd", "\t=1", "\r=1"])
def test_csv_safe_quotes_formula_prefixes(value):
    assert csv_safe(value).startswith("'")


def test_csv_safe_leaves_plain_text():
    assert csv_safe("Айгуль") == "Айгуль" and csv_safe("") == ""


# --- IIN -----------------------------------------------------------------------------------------------------------

def test_iin_rejects_impossible_century_digit():
    iin = generate_iin()
    bad = iin[:6] + "9" + iin[7:]
    with pytest.raises(InvalidIINError):
        validate_iin(bad)


def test_iin_rejects_impossible_calendar_date():
    iin = generate_iin()
    bad = iin[:2] + "0231" + iin[6:]  # 31 February
    with pytest.raises(InvalidIINError):
        validate_iin(bad)


def test_iin_birth_date_decodes_century():
    iin = generate_iin()
    born = birth_date(iin)
    assert isinstance(born, date) and 1960 <= born.year <= 1999


# --- one discount per sale -------------------------------------------------------------------------------------------

def test_contract_cannot_discount_already_discounted_enrollment(client):
    _login(client)
    courses = client.get("/api/courses").json()
    customers = client.get("/api/customers").json()["items"]
    enr = client.post("/api/enrollments", json={"client_id": customers[0]["id"], "course_id": courses[0]["id"], "discount_pct": 10}).json()
    r = client.post(
        "/api/contracts",
        json={"client_id": customers[0]["id"], "number": "BA-DISC-001", "enrollment_ids": [enr[0]["id"]], "discount_pct": 10},
    )
    assert r.status_code == 409
    r = client.post(
        "/api/contracts",
        json={"client_id": customers[0]["id"], "number": "BA-DISC-002", "enrollment_ids": [enr[0]["id"]], "discount_pct": 0},
    )
    assert r.status_code == 201 and Decimal(r.json()["total_kzt"]) == Decimal(enr[0]["price_kzt"])


# --- domain errors through the single handler -------------------------------------------------------------------------

def test_domain_error_handler_formats_detail(client):
    _login(client)
    r = client.get("/api/clients/999999/contracts")
    assert r.status_code == 404 and r.json() == {"detail": "Not found"}
    r = client.post("/api/integrations/1c/import", content=b"<not xml", headers={"Content-Type": "application/xml"})
    assert r.status_code == 400 and r.json()["detail"] == "Malformed XML"
