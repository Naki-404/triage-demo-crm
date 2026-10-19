"""Stand attack-log simulation (local lab only)."""
from __future__ import annotations

from app.config import settings


def _login(client, username="admin", password="Admin-2026!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def test_simulate_catalog_and_brute_force(client, monkeypatch):
    monkeypatch.setattr(settings, "STAND_CONTROL_ENABLED", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    _login(client)

    catalog = client.get("/api/stand/simulate")
    assert catalog.status_code == 200
    ids = {s["id"] for s in catalog.json()["scenarios"]}
    assert "brute_force" in ids and "privilege_escalation" in ids

    r = client.post("/api/stand/simulate", json={"scenario": "brute_force", "count": 3})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scenario"] == "brute_force"
    assert body["events"] == 3
    assert body["shipped"] is True
    assert len(body["request_ids"]) == 3


def test_simulate_unknown_scenario(client, monkeypatch):
    monkeypatch.setattr(settings, "STAND_CONTROL_ENABLED", True)
    _login(client)
    r = client.post("/api/stand/simulate", json={"scenario": "not_a_real_attack"})
    assert r.status_code == 422


def test_simulate_disabled_in_production(client, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "STAND_CONTROL_ENABLED", True)
    _login(client)
    r = client.post("/api/stand/simulate", json={"scenario": "brute_force"})
    assert r.status_code == 403


def test_simulate_admin_only(client, monkeypatch):
    monkeypatch.setattr(settings, "STAND_CONTROL_ENABLED", True)
    _login(client, "manager", "Manager-2026!")
    r = client.post("/api/stand/simulate", json={"scenario": "brute_force"})
    assert r.status_code == 403


def test_simulate_custom_manual_log(client, monkeypatch):
    monkeypatch.setattr(settings, "STAND_CONTROL_ENABLED", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    _login(client)
    r = client.post(
        "/api/stand/simulate/custom",
        json={
            "message": "manual privilege check failed for manager",
            "level": "error",
            "method": "PATCH",
            "path": "/api/auth/me",
            "status_code": 403,
            "attack": "T1078",
            "count": 2,
            "body": '{"role":"admin"}',
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scenario"] == "custom"
    assert body["events"] == 2
    assert body["shipped"] is True
    assert len(body["request_ids"]) == 2


def test_simulate_custom_requires_message(client, monkeypatch):
    monkeypatch.setattr(settings, "STAND_CONTROL_ENABLED", True)
    _login(client)
    r = client.post("/api/stand/simulate/custom", json={"message": ""})
    assert r.status_code == 422
