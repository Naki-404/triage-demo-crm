"""One clean/vuln pair per VULN_* flag: the clean path must refuse the attack, the vuln path must let it through.

XSS, XXE and open redirect are imitations at the API level (see docs/VULN_FLAGS.md): the response carries the
payload or the redirect header, the actual exploitation happens in a browser or an XML consumer we do not ship.
"""
from __future__ import annotations

import json
import time
from decimal import Decimal

import pytest

from app.config import settings
from app.stand_flags import VULN_KEYS


def _login(client, username="admin", password="Admin-2026!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r


def _create_client(client, name="Пара Тестова", iin=None):
    from app.iin import generate_iin
    import random

    r = client.post("/api/customers", json={"name": name, "iin": iin or generate_iin(random.Random(7)), "phone": "+77010000099"})
    assert r.status_code == 201, r.text
    return r.json()


def test_every_flag_has_a_pair():
    covered = {name.split("test_", 1)[1].rsplit("_", 1)[0].upper() for name in globals() if name.startswith("test_vuln_")}
    missing = [k for k in VULN_KEYS if k not in covered]
    assert not missing, missing


# VULN_SQLI_SEARCH ------------------------------------------------------------------------------------------------

def test_vuln_sqli_search_clean(client):
    _login(client)
    r = client.get("/api/customers/search", params={"name": "x' OR '1'='1"})
    assert r.status_code == 200 and r.json() == []


def test_vuln_sqli_search_vuln(client, stand_mode):
    stand_mode("vuln", VULN_SQLI_SEARCH=True)
    _login(client)
    r = client.get("/api/customers/search", params={"name": "x' OR '1'='1"})
    assert r.status_code == 200 and len(r.json()) >= 2


# VULN_IDOR_CUSTOMER ----------------------------------------------------------------------------------------------

def test_vuln_idor_customer_clean(client):
    _login(client)
    foreign = _create_client(client)
    client.post("/api/auth/logout")
    _login(client, "manager", "Manager-2026!")
    assert client.get(f"/api/customers/{foreign['id']}").status_code == 404
    assert client.get(f"/api/customers/{foreign['id']}/notes").status_code == 404


def test_vuln_idor_customer_vuln(client, stand_mode):
    _login(client)
    foreign = _create_client(client)
    client.post("/api/auth/logout")
    stand_mode("vuln", VULN_IDOR_CUSTOMER=True)
    _login(client, "manager", "Manager-2026!")
    assert client.get(f"/api/customers/{foreign['id']}").status_code == 200


# VULN_MASS_ASSIGNMENT --------------------------------------------------------------------------------------------

def test_vuln_mass_assignment_clean(client):
    _login(client, "manager", "Manager-2026!")
    r = client.patch("/api/auth/me", json={"role": "admin"})
    assert r.status_code == 200 and r.json()["role"] == "manager"


def test_vuln_mass_assignment_vuln(client, stand_mode):
    stand_mode("vuln", VULN_MASS_ASSIGNMENT=True)
    _login(client, "manager", "Manager-2026!")
    r = client.patch("/api/auth/me", json={"role": "admin"})
    assert r.status_code == 200 and r.json()["role"] == "admin"


# VULN_STORED_XSS_NOTES -------------------------------------------------------------------------------------------

PAYLOAD = '<img src=x onerror="alert(1)">'


def test_vuln_stored_xss_notes_clean(client):
    _login(client)
    cid = client.get("/api/customers").json()["items"][0]["id"]
    r = client.post(f"/api/customers/{cid}/notes", json={"body": PAYLOAD})
    assert r.status_code == 201
    assert "<img" not in r.json()["body"] and "&lt;img" in r.json()["body"]
    assert "&quot;" in r.json()["body"]


def test_vuln_stored_xss_notes_vuln(client, stand_mode):
    stand_mode("vuln", VULN_STORED_XSS_NOTES=True)
    _login(client)
    cid = client.get("/api/customers").json()["items"][0]["id"]
    r = client.post(f"/api/customers/{cid}/notes", json={"body": PAYLOAD})
    assert r.status_code == 201 and r.json()["body"] == PAYLOAD


# VULN_PATH_TRAVERSAL_EXPORT --------------------------------------------------------------------------------------

@pytest.fixture()
def export_dir(tmp_path):
    (tmp_path / "secret.txt").write_text("outside", encoding="utf-8")
    old = settings.EXPORT_DIR
    settings.EXPORT_DIR = str(tmp_path / "exports")
    yield tmp_path
    settings.EXPORT_DIR = old


def test_vuln_path_traversal_export_clean(client, export_dir):
    _login(client)
    r = client.get("/api/customers/export/file", params={"name": "../secret.txt"})
    assert r.status_code == 404


def test_vuln_path_traversal_export_vuln(client, export_dir, stand_mode):
    stand_mode("vuln", VULN_PATH_TRAVERSAL_EXPORT=True)
    _login(client)
    r = client.get("/api/customers/export/file", params={"name": "../secret.txt"})
    assert r.status_code == 200 and r.content == b"outside"


# VULN_SSRF_WEBHOOK -----------------------------------------------------------------------------------------------

def test_vuln_ssrf_webhook_clean(client):
    _login(client, "manager", "Manager-2026!")
    for url in ("http://127.0.0.1:1/admin", "http://localhost:1/", "http://169.254.169.254/latest/meta-data/", "file:///etc/passwd", "http://user:pw@example.com/"):
        r = client.patch("/api/auth/me", json={"webhook_url": url})
        assert r.status_code == 400, url
    assert client.get("/api/auth/me").json()["webhook_url"] is None


def test_vuln_ssrf_webhook_vuln(client, stand_mode):
    stand_mode("vuln", VULN_SSRF_WEBHOOK=True)
    _login(client, "manager", "Manager-2026!")
    r = client.patch("/api/auth/me", json={"webhook_url": "http://127.0.0.1:1/admin"})
    assert r.status_code == 200 and r.json()["webhook_url"] == "http://127.0.0.1:1/admin"
    r = client.post("/api/auth/me/webhook/test")
    # The request is actually sent to the loopback address (nothing listens on port 1, hence 502).
    assert r.status_code == 502 and "unreachable" in r.json()["detail"]


# VULN_XXE_1C_IMPORT ----------------------------------------------------------------------------------------------

XXE = b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><Document><Number>&xxe;</Number></Document>'


def test_vuln_xxe_1c_import_clean(client):
    _login(client)
    r = client.post("/api/integrations/1c/import", content=XXE, headers={"Content-Type": "application/xml"})
    assert r.status_code == 400
    utf16 = XXE.decode().encode("utf-16")
    r = client.post("/api/integrations/1c/import", content=utf16, headers={"Content-Type": "application/xml"})
    assert r.status_code == 400


def test_vuln_xxe_1c_import_vuln(client, stand_mode):
    stand_mode("vuln", VULN_XXE_1C_IMPORT=True)
    _login(client)
    r = client.post("/api/integrations/1c/import", content=XXE, headers={"Content-Type": "application/xml"})
    assert r.status_code == 500 and "XXE" in r.json()["detail"]


# VULN_NO_RATE_LIMIT_LOGIN ----------------------------------------------------------------------------------------

def test_vuln_no_rate_limit_login_clean(client):
    for _ in range(settings.LOGIN_MAX_FAILURES):
        assert client.post("/api/auth/login", json={"username": "manager", "password": "wrong"}).status_code == 401
    r = client.post("/api/auth/login", json={"username": "manager", "password": "Manager-2026!"})
    assert r.status_code == 401


def test_vuln_no_rate_limit_login_vuln(client, stand_mode):
    stand_mode("vuln", VULN_NO_RATE_LIMIT_LOGIN=True)
    for _ in range(settings.LOGIN_MAX_FAILURES + 2):
        assert client.post("/api/auth/login", json={"username": "manager", "password": "wrong"}).status_code == 401
    r = client.post("/api/auth/login", json={"username": "manager", "password": "Manager-2026!"})
    assert r.status_code == 200


# VULN_OPEN_REDIRECT ----------------------------------------------------------------------------------------------

def test_vuln_open_redirect_clean(client):
    r = client.post("/api/auth/login?next=https://evil.example/phish", json={"username": "admin", "password": "Admin-2026!"})
    assert r.status_code == 200 and "X-Redirect-To" not in r.headers
    r = client.post("/api/auth/login?next=/clients/1", json={"username": "admin", "password": "Admin-2026!"})
    assert r.headers.get("X-Redirect-To") == "/clients/1"


def test_vuln_open_redirect_vuln(client, stand_mode):
    stand_mode("vuln", VULN_OPEN_REDIRECT=True)
    r = client.post("/api/auth/login?next=https://evil.example/phish", json={"username": "admin", "password": "Admin-2026!"})
    assert r.headers.get("X-Redirect-To") == "https://evil.example/phish"


# VULN_CSV_INJECTION ----------------------------------------------------------------------------------------------

def _export_rows(client):
    r = client.get("/api/customers/export", params={"fmt": "csv"})
    assert r.status_code == 200
    return r.content.decode("utf-8")


def test_vuln_csv_injection_clean(client, export_dir):
    _login(client)
    _create_client(client, name='=HYPERLINK("http://evil","x")')
    body = _export_rows(client)
    assert "'=HYPERLINK" in body and ',=HYPERLINK' not in body


def test_vuln_csv_injection_vuln(client, export_dir, stand_mode):
    stand_mode("vuln", VULN_CSV_INJECTION=True)
    _login(client)
    _create_client(client, name='=HYPERLINK("http://evil","x")')
    body = _export_rows(client)
    assert '"=HYPERLINK' in body and "'=HYPERLINK" not in body


# VULN_PRICE_TAMPERING --------------------------------------------------------------------------------------------

def _enroll(client, price):
    courses = client.get("/api/courses").json()
    customers = client.get("/api/customers").json()["items"]
    r = client.post("/api/enrollments", json={"client_id": customers[0]["id"], "course_id": courses[0]["id"], "price_kzt": str(price)})
    assert r.status_code == 201, r.text
    return Decimal(r.json()[0]["price_kzt"]), Decimal(courses[0]["price_kzt"])


def test_vuln_price_tampering_clean(client):
    _login(client)
    price, listed = _enroll(client, 1)
    assert price == listed


def test_vuln_price_tampering_vuln(client, stand_mode):
    stand_mode("vuln", VULN_PRICE_TAMPERING=True)
    _login(client)
    price, listed = _enroll(client, 1)
    assert price == Decimal("1") and price != listed


# VULN_PAYMENT_SIGNATURE ------------------------------------------------------------------------------------------

def _webhook(client, signature="bad"):
    body = json.dumps({"contract_id": 99999, "amount_kzt": "1000", "external_id": "pair-1"}).encode()
    return client.post(
        "/api/payments/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": signature, "X-Timestamp": str(int(time.time()))},
    )


def test_vuln_payment_signature_clean(client):
    assert _webhook(client).status_code == 401


def test_vuln_payment_signature_vuln(client, stand_mode):
    stand_mode("vuln", VULN_PAYMENT_SIGNATURE=True)
    # The signature is skipped, so the request reaches the contract lookup (404 for an unknown contract).
    assert _webhook(client).status_code == 404
