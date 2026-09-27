"""Bilim commerce: enrollments, installments, discount limits."""
from __future__ import annotations

from decimal import Decimal

from app.config import settings


def _login(c, user="manager", password="Manager-2026!"):
    assert c.post("/api/auth/login", json={"username": user, "password": password}).status_code == 200


def test_discount_limit_403(client):
    settings.CRM_MODE = "clean"
    _login(client)
    courses = client.get("/api/courses").json()
    assert courses
    customers = client.get("/api/customers").json()["items"]
    assert customers
    r = client.post(
        "/api/enrollments",
        json={"client_id": customers[0]["id"], "course_id": courses[0]["id"], "discount_pct": 50},
    )
    assert r.status_code == 403


def test_duplicate_enrollment_409(client):
    settings.CRM_MODE = "clean"
    settings.FAULT_DUPLICATE_ENROLLMENT = False
    _login(client)
    courses = client.get("/api/courses").json()
    customers = client.get("/api/customers").json()["items"]
    payload = {"client_id": customers[0]["id"], "course_id": courses[0]["id"], "discount_pct": 0}
    assert client.post("/api/enrollments", json=payload).status_code == 201
    r = client.post("/api/enrollments", json=payload)
    assert r.status_code == 409


def test_installment_sum_matches_total(client):
    settings.CRM_MODE = "clean"
    settings.FAULT_INSTALLMENT_ROUNDING = False
    _login(client, "admin", "Admin-2026!")
    courses = client.get("/api/courses").json()
    customers = client.get("/api/customers").json()["items"]
    enr = client.post(
        "/api/enrollments",
        json={"client_id": customers[1]["id"], "course_id": courses[0]["id"], "discount_pct": 0},
    ).json()
    contract = client.post(
        "/api/contracts",
        json={"client_id": customers[1]["id"], "number": "BA-TEST-001", "enrollment_ids": [enr[0]["id"]], "discount_pct": 0},
    ).json()
    plan = client.post(f"/api/contracts/{contract['id']}/installments", json={"months": 3}).json()
    total = sum(Decimal(p["amount_kzt"]) for p in plan)
    assert total == Decimal(contract["total_kzt"])
