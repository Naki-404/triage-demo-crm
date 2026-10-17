"""Demo database and the overview/list screens (dashboard, contracts, payments, desk payments)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.demo_data import DEMO_CLIENTS, populate
from app.iin import check_digit
from app.models import Client, Contract, ContractStatus, Installment, InstallmentStatus, Payment, PaymentStatus


def _login(client, username="admin", password="Admin-2026!"):
    assert client.post("/api/auth/login", json={"username": username, "password": password}).status_code == 200


def _populate(db_session):
    return populate(db_session, lambda name: f"{name.title()}-2026!", today=date(2026, 10, 17))


def test_demo_year_is_consistent_and_idempotent(client, db_session):
    counts = _populate(db_session)
    assert counts["clients"] == DEMO_CLIENTS and counts["contracts"] > 100 and counts["payments"] > 150
    assert _populate(db_session)["clients"] == 0  # second run adds nothing
    demo = db_session.query(Client).filter(Client.meta_json.isnot(None)).all()
    assert all(check_digit(c.iin[:11]) == int(c.iin[11]) for c in demo)
    assert len({c.iin for c in db_session.query(Client).all()}) == db_session.query(Client).count()
    for contract in db_session.query(Contract).all():
        rows = db_session.query(Installment).filter(Installment.contract_id == contract.id).all()
        if rows:
            assert sum((r.amount_kzt for r in rows), Decimal("0")) == contract.total_kzt
        paid = sum((p.amount_kzt for p in db_session.query(Payment).filter(
            Payment.contract_id == contract.id, Payment.status == PaymentStatus.paid)), Decimal("0"))
        assert paid <= contract.total_kzt
        if contract.status == ContractStatus.completed:
            assert paid == contract.total_kzt
        if contract.status == ContractStatus.draft:
            assert paid == 0 and not rows
    assert db_session.query(Installment).filter(Installment.status == InstallmentStatus.overdue).count() > 0


def test_dashboard_and_lists_are_scoped_to_the_manager(client, db_session):
    _populate(db_session)
    _login(client)
    admin = client.get("/api/dashboard").json()
    assert admin["clients_total"] >= DEMO_CLIENTS and len(admin["revenue_by_month"]) == 6
    client.post("/api/auth/logout")
    _login(client, "manager", "Manager-2026!")
    mine = client.get("/api/dashboard").json()
    assert 0 < mine["clients_total"] < admin["clients_total"]
    own_ids = {c.id for c in db_session.query(Client).filter(Client.owner_id == 2)}
    contracts = client.get("/api/contracts", params={"page_size": 100}).json()
    assert contracts["total"] > 0 and all(row["client_id"] in own_ids for row in contracts["items"])
    payments = client.get("/api/payments", params={"page_size": 100}).json()
    assert all(row["client_id"] in own_ids for row in payments["items"])
    foreign = db_session.query(Contract).join(Client).filter(Client.owner_id != 2).first()
    assert client.get(f"/api/contracts/{foreign.id}").status_code == 404


def test_sign_and_take_payment_settles_installments(client, db_session):
    _login(client)
    customer = client.get("/api/customers").json()["items"][0]
    course = client.get("/api/courses").json()[0]
    enr = client.post("/api/enrollments", json={"client_id": customer["id"], "course_id": course["id"]}).json()[0]
    contract = client.post("/api/contracts", json={"client_id": customer["id"], "number": "BA-T-1", "enrollment_ids": [enr["id"]]}).json()
    row = db_session.get(Contract, contract["id"])  # the desk flow creates signed contracts; demo data also has drafts
    row.status, row.signed_at = ContractStatus.draft, None
    db_session.commit()
    assert client.post(f"/api/contracts/{contract['id']}/payments", json={"amount_kzt": 1000}).status_code == 409  # draft
    assert client.post(f"/api/contracts/{contract['id']}/sign").json()["status"] == "active"
    client.post(f"/api/contracts/{contract['id']}/installments", json={"months": 3})
    first = client.get(f"/api/contracts/{contract['id']}").json()["installments"][0]
    detail = client.post(f"/api/contracts/{contract['id']}/payments", json={"amount_kzt": first["amount_kzt"], "method": "kaspi"}).json()
    assert [i["status"] for i in detail["installments"]] == ["paid", "scheduled", "scheduled"]
    assert Decimal(detail["paid_kzt"]) == Decimal(first["amount_kzt"])
    rest = Decimal(detail["total_kzt"]) - Decimal(detail["paid_kzt"])
    done = client.post(f"/api/contracts/{contract['id']}/payments", json={"amount_kzt": str(rest)}).json()
    assert done["status"] == "completed"
    client.post("/api/auth/logout")
    _login(client, "viewer", "Viewer-2026!")
    assert client.post(f"/api/contracts/{contract['id']}/sign").status_code == 403


def test_demo_has_nothing_in_the_future_and_can_be_reset(client, db_session):
    from datetime import datetime

    from app.demo_data import reset

    populate(db_session, lambda name: f"{name.title()}-2026!")
    now = datetime.now()
    assert all(p.paid_at is None or p.paid_at <= now for p in db_session.query(Payment))
    assert all(c.created_at <= now for c in db_session.query(Client))
    assert reset(db_session) == DEMO_CLIENTS
    assert db_session.query(Client).filter(Client.meta_json.isnot(None)).count() == 0
