"""Clean vs vuln behaviour for intentional vulnerability flags."""
from __future__ import annotations

import json
import time

from app.config import settings


def _login(client, username="admin", password="Admin-2026!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200


def test_vuln_sqli_clean_blocks_injection(client):
    settings.CRM_MODE = "clean"
    settings.VULN_SQLI_SEARCH = False
    _login(client)
    r = client.get("/api/customers/search", params={"name": "x' OR '1'='1"})
    assert r.status_code == 200
    assert r.json() == []


def test_vuln_sqli_vuln_mode_executes_raw(client):
    settings.CRM_MODE = "vuln"
    settings.VULN_SQLI_SEARCH = True
    _login(client)
    r = client.get("/api/customers/search", params={"name": "x' OR '1'='1"})
    assert r.status_code in (200, 500)
    settings.CRM_MODE = "clean"
    settings.VULN_SQLI_SEARCH = False


def test_mass_assignment_clean_ignores_role(client):
    settings.CRM_MODE = "clean"
    settings.VULN_MASS_ASSIGNMENT = False
    _login(client, "manager", "Manager-2026!")
    r = client.patch("/api/auth/me", json={"role": "admin"})
    assert r.status_code == 200
    assert r.json()["role"] == "manager"


def test_mass_assignment_vuln_accepts_role(client):
    settings.CRM_MODE = "vuln"
    settings.VULN_MASS_ASSIGNMENT = True
    _login(client, "manager", "Manager-2026!")
    r = client.patch("/api/auth/me", json={"role": "admin"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    settings.CRM_MODE = "clean"
    settings.VULN_MASS_ASSIGNMENT = False


def test_payment_signature_required_in_clean(client):
    settings.CRM_MODE = "clean"
    settings.VULN_PAYMENT_SIGNATURE = False
    body = json.dumps({"contract_id": 1, "amount_kzt": "1000", "external_id": "x1"}).encode()
    r = client.post(
        "/api/payments/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": "bad", "X-Timestamp": str(int(time.time()))},
    )
    assert r.status_code in (401, 404, 400)


def test_payment_signature_skipped_in_vuln(client):
    settings.CRM_MODE = "vuln"
    settings.VULN_PAYMENT_SIGNATURE = True
    body = json.dumps({"contract_id": 99999, "amount_kzt": "1000", "external_id": "x2"}).encode()
    r = client.post(
        "/api/payments/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": "", "X-Timestamp": str(int(time.time()))},
    )
    assert r.status_code == 404
    settings.CRM_MODE = "clean"
    settings.VULN_PAYMENT_SIGNATURE = False


def test_xxe_blocked_in_clean(client):
    settings.CRM_MODE = "clean"
    settings.VULN_XXE_1C_IMPORT = False
    _login(client)
    raw = b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><Document><Number>&xxe;</Number></Document>'
    r = client.post("/api/integrations/1c/import", content=raw, headers={"Content-Type": "application/xml"})
    assert r.status_code == 400
