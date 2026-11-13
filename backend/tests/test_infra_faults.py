"""Infrastructure / stored-data stand faults (services/infra_faults.py): off in clean mode; in experiment mode each
fails with the message the real component would give."""
from __future__ import annotations

import random

from app.iin import generate_iin

INFRA_KEYS = ("FAULT_CACHE_DOWN", "FAULT_TAX_DNS", "FAULT_TAX_CERT", "FAULT_ID_SEQUENCE", "FAULT_FK_ORPHAN",
              "FAULT_BROKER_DOWN", "FAULT_DB_READONLY", "FAULT_CLOCK_SKEW")


def _login(client):
    assert client.post("/api/auth/login", json={"username": "admin", "password": "Admin-2026!"}).status_code == 200


def _new_client(client, rng=random.Random(11)):
    r = client.post("/api/customers", json={"name": "Тест Инфра", "iin": generate_iin(rng)})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _contract(client, cid):
    course = client.get("/api/courses").json()[0]
    enr = client.post("/api/enrollments", json={"client_id": cid, "course_id": course["id"]}).json()[0]
    r = client.post("/api/contracts", json={"client_id": cid, "number": f"BA-IF-{cid}", "enrollment_ids": [enr["id"]]})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_infra_faults_are_off_in_clean_mode(client, monkeypatch):
    from app.config import settings

    for key in INFRA_KEYS:
        monkeypatch.setattr(settings, key, True)  # flags alone do nothing outside CRM_MODE=experiment
    _login(client)
    cid = _new_client(client)
    contract = _contract(client, cid)
    assert client.get("/api/courses").status_code == 200
    assert client.get(f"/api/clients/{cid}/contracts").status_code == 200
    assert client.post(f"/api/contracts/{contract}/installments", json={"months": 3}).status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_cache_down(client, stand_mode):
    _login(client)
    stand_mode("experiment", FAULT_CACHE_DOWN=True)
    r = client.get("/api/courses")
    assert r.status_code == 503 and "Connection refused" in r.json()["detail"]


def test_id_sequence_behind(client, stand_mode):
    _login(client)
    stand_mode("experiment", FAULT_ID_SEQUENCE=True)
    r = client.post("/api/customers", json={"name": "Тест Инфра", "iin": generate_iin(random.Random(12))})
    assert r.status_code == 500 and "clients_pkey" in r.json()["detail"]


def test_fk_orphan(client, stand_mode):
    _login(client)
    cid = _new_client(client)
    _contract(client, cid)
    stand_mode("experiment", FAULT_FK_ORPHAN=True)
    r = client.get(f"/api/clients/{cid}/contracts")
    assert r.status_code == 500 and "does not exist" in r.json()["detail"]


def test_broker_down(client, stand_mode):
    _login(client)
    contract = _contract(client, _new_client(client))
    stand_mode("experiment", FAULT_BROKER_DOWN=True)
    r = client.post(f"/api/contracts/{contract}/installments", json={"months": 6})
    assert r.status_code == 503 and "broker" in r.json()["detail"]


def test_db_read_only(client, stand_mode):
    _login(client)
    cid = _new_client(client)
    stand_mode("experiment", FAULT_DB_READONLY=True)
    r = client.post(f"/api/customers/{cid}/notes", json={"body": "Перезвонить"})
    assert r.status_code == 503 and "read-only" in r.json()["detail"]


def test_clock_skew(client, stand_mode):
    _login(client)
    stand_mode("experiment", FAULT_CLOCK_SKEW=True)
    r = client.get("/api/auth/me")
    assert r.status_code == 401 and "NTP" in r.json()["detail"]


def test_tax_dns_failure(client, stand_mode):
    _login(client)
    cid = _new_client(client)
    stand_mode("experiment", FAULT_TAX_DNS=True)
    r = client.get(f"/api/customers/{cid}/tax")
    assert r.status_code == 503 and "name resolution" in r.json()["detail"]


def test_tax_cert_expired(client, stand_mode):
    _login(client)
    cid = _new_client(client)
    stand_mode("experiment", FAULT_TAX_CERT=True)
    r = client.get(f"/api/customers/{cid}/tax")
    assert r.status_code == 503 and "certificate has expired" in r.json()["detail"]
