"""Data-layer stand faults: each is off in clean mode and, in experiment mode, fails the way a real data problem does."""
from __future__ import annotations

import random

import pytest

from app.iin import generate_iin


def _login(client):
    assert client.post("/api/auth/login", json={"username": "admin", "password": "Admin-2026!"}).status_code == 200


def _new_client(client, rng=random.Random(7)):
    iin = generate_iin(rng)
    r = client.post("/api/customers", json={"name": "Тест Данных", "iin": iin})
    assert r.status_code == 201, r.text
    return r.json()["id"], iin


def _contract_for(client, cid):
    course = client.get("/api/courses").json()[0]
    enr = client.post("/api/enrollments", json={"client_id": cid, "course_id": course["id"]}).json()[0]
    assert client.post("/api/contracts", json={"client_id": cid, "number": f"BA-DF-{cid}", "enrollment_ids": [enr["id"]]}).status_code == 201


def test_data_faults_are_off_in_clean_mode(client, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "EXPORT_DIR", str(tmp_path))
    for key in ("FAULT_REPLICA_LAG", "FAULT_LEGACY_AMOUNT", "FAULT_DISK_FULL"):
        monkeypatch.setattr(settings, key, True)  # flags alone do nothing outside CRM_MODE=experiment
    _login(client)
    cid, iin = _new_client(client)
    _contract_for(client, cid)
    assert client.get("/api/customers/search", params={"iin": iin}).status_code == 200
    assert client.get(f"/api/customers/{cid}").status_code == 200
    assert client.get(f"/api/clients/{cid}/contracts").status_code == 200
    assert client.get("/api/customers/export", params={"fmt": "csv"}).status_code == 200


def test_replica_lag_answers_503(client, stand_mode):
    _login(client)
    cid, _ = _new_client(client)
    stand_mode("experiment", FAULT_REPLICA_LAG=True)
    r = client.get(f"/api/customers/{cid}")
    assert r.status_code == 503 and "replica" in r.json()["detail"]


def test_legacy_amount_overflow_on_contract_list(client, stand_mode):
    _login(client)
    cid, _ = _new_client(client)
    _contract_for(client, cid)
    stand_mode("experiment", FAULT_LEGACY_AMOUNT=True)
    r = client.get(f"/api/clients/{cid}/contracts")
    assert r.status_code == 500 and "NUMERIC(12,2)" in r.json()["detail"]


def test_disk_full_on_export(client, stand_mode, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "EXPORT_DIR", str(tmp_path))
    _login(client)
    stand_mode("experiment", FAULT_DISK_FULL=True)
    # the unhandled OSError reaches the generic handler (500 + Sentry); the test client re-raises it
    with pytest.raises(OSError, match="No space left on device"):
        client.get("/api/customers/export", params={"fmt": "csv"})
