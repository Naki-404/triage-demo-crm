"""Overview and list screens: dashboard, contracts, payments; signing a contract and taking a payment at the desk.

Every query is scoped like the client list: a manager sees the contracts and payments of their own clients.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import vulns
from ..auth import require_roles
from ..db import get_db
from ..models import (
    Client,
    Contract,
    ContractStatus,
    Course,
    Enrollment,
    Installment,
    InstallmentStatus,
    Payment,
    PaymentStatus,
    User,
    UserRole,
    utcnow,
)
from ..services import payments as payment_service
from ..services.commerce_pricing import CommerceError

router = APIRouter(prefix="/api", tags=["reports"])
ANY_ROLE = require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)
WRITE_ROLE = require_roles(UserRole.admin, UserRole.manager)


def _scope(query, user: User):
    """The same rule as the client list: managers see their own clients only."""
    if user.role == UserRole.manager and not vulns.idor_customer():
        return query.filter(Client.owner_id == user.id)
    return query


def _overdue_filter(today: date):
    return (Installment.status == InstallmentStatus.overdue) | (
        (Installment.status == InstallmentStatus.scheduled) & (Installment.due_date < today)
    )


# ---------------------------------------------------------------------------------------------------- dashboard
class MonthAmount(BaseModel):
    month: str
    amount_kzt: Decimal


class CourseCount(BaseModel):
    code: str
    title: str
    enrollments: int


class PaymentRow(BaseModel):
    id: int
    contract_id: int
    contract_number: str
    client_id: int
    client_name: str
    amount_kzt: Decimal
    status: PaymentStatus
    card_last4: str | None
    paid_at: datetime | None
    created_at: datetime


class DueRow(BaseModel):
    installment_id: int
    contract_id: int
    contract_number: str
    client_id: int
    client_name: str
    seq: int
    due_date: date
    amount_kzt: Decimal
    overdue: bool


class DashboardOut(BaseModel):
    clients_total: int
    clients_new_30d: int
    contracts_active: int
    contracts_draft: int
    revenue_month_kzt: Decimal
    revenue_prev_month_kzt: Decimal
    overdue_count: int
    overdue_kzt: Decimal
    revenue_by_month: list[MonthAmount]
    top_courses: list[CourseCount]
    recent_payments: list[PaymentRow]
    upcoming: list[DueRow]


def _month_start(d: date, back: int = 0) -> date:
    year, month = d.year, d.month - back
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _payment_rows(rows) -> list[PaymentRow]:
    return [PaymentRow(id=p.id, contract_id=c.id, contract_number=c.number, client_id=cl.id, client_name=cl.name, amount_kzt=p.amount_kzt,
                       status=p.status, card_last4=p.card_last4, paid_at=p.paid_at, created_at=p.created_at) for p, c, cl in rows]


def _due_rows(rows, today: date) -> list[DueRow]:
    return [DueRow(installment_id=i.id, contract_id=c.id, contract_number=c.number, client_id=cl.id, client_name=cl.name, seq=i.seq,
                   due_date=i.due_date, amount_kzt=i.amount_kzt, overdue=i.status == InstallmentStatus.overdue or i.due_date < today)
            for i, c, cl in rows]


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), user: User = Depends(ANY_ROLE)):
    today = date.today()
    clients = _scope(db.query(Client), user)
    contracts = _scope(db.query(Contract).join(Client, Contract.client_id == Client.id), user)
    paid = _scope(db.query(Payment).join(Contract, Payment.contract_id == Contract.id).join(Client, Contract.client_id == Client.id), user).filter(
        Payment.status == PaymentStatus.paid)
    months = []
    for back in range(5, -1, -1):
        start, end = _month_start(today, back), _month_start(today, back - 1) if back else _month_start(today, -1)
        amount = paid.filter(Payment.paid_at >= start, Payment.paid_at < end).with_entities(func.coalesce(func.sum(Payment.amount_kzt), 0)).scalar()
        months.append(MonthAmount(month=start.strftime("%Y-%m"), amount_kzt=Decimal(amount)))
    installments = _scope(db.query(Installment, Contract, Client).join(Contract, Installment.contract_id == Contract.id)
                          .join(Client, Contract.client_id == Client.id), user)
    overdue = installments.filter(_overdue_filter(today), Contract.status == ContractStatus.active)
    top = _scope(db.query(Course.code, Course.title, func.count(Enrollment.id)).join(Enrollment, Enrollment.course_id == Course.id)
                 .join(Client, Enrollment.client_id == Client.id), user).group_by(Course.id).order_by(func.count(Enrollment.id).desc()).limit(5).all()
    recent = _scope(db.query(Payment, Contract, Client).join(Contract, Payment.contract_id == Contract.id)
                    .join(Client, Contract.client_id == Client.id), user).order_by(Payment.created_at.desc()).limit(8).all()
    upcoming = installments.filter(Installment.status.in_([InstallmentStatus.scheduled, InstallmentStatus.overdue]),
                                   Contract.status == ContractStatus.active).order_by(Installment.due_date).limit(8).all()
    return DashboardOut(
        clients_total=clients.count(),
        clients_new_30d=clients.filter(Client.created_at >= utcnow() - timedelta(days=30)).count(),
        contracts_active=contracts.filter(Contract.status == ContractStatus.active).count(),
        contracts_draft=contracts.filter(Contract.status == ContractStatus.draft).count(),
        revenue_month_kzt=months[-1].amount_kzt,
        revenue_prev_month_kzt=months[-2].amount_kzt,
        overdue_count=overdue.count(),
        overdue_kzt=Decimal(overdue.with_entities(func.coalesce(func.sum(Installment.amount_kzt), 0)).scalar()),
        revenue_by_month=months,
        top_courses=[CourseCount(code=c, title=t, enrollments=n) for c, t, n in top],
        recent_payments=_payment_rows(recent),
        upcoming=_due_rows(upcoming, today),
    )


# ---------------------------------------------------------------------------------------------------- contracts
class ContractRow(BaseModel):
    id: int
    number: str
    client_id: int
    client_name: str
    status: ContractStatus
    total_kzt: Decimal
    paid_kzt: Decimal
    discount_pct: int
    created_at: datetime
    signed_at: datetime | None
    next_due: date | None
    overdue: bool


class ContractPage(BaseModel):
    items: list[ContractRow]
    total: int
    page: int
    page_size: int


class InstallmentRow(BaseModel):
    id: int
    seq: int
    due_date: date
    amount_kzt: Decimal
    status: InstallmentStatus
    overdue: bool


class EnrollmentRow(BaseModel):
    id: int
    course_code: str
    course_title: str
    price_kzt: Decimal
    discount_pct: int


class ContractDetail(ContractRow):
    installments: list[InstallmentRow]
    payments: list[PaymentRow]
    enrollments: list[EnrollmentRow]


def _paid_sum(db: Session, contract_id: int) -> Decimal:
    value = db.query(func.coalesce(func.sum(Payment.amount_kzt), 0)).filter(
        Payment.contract_id == contract_id, Payment.status == PaymentStatus.paid).scalar()
    return Decimal(value)


def _contract_row(db: Session, contract: Contract, client: Client, today: date) -> ContractRow:
    pending = (db.query(Installment).filter(Installment.contract_id == contract.id,
                                             Installment.status.in_([InstallmentStatus.scheduled, InstallmentStatus.overdue]))
               .order_by(Installment.due_date).all())
    return ContractRow(
        id=contract.id, number=contract.number, client_id=client.id, client_name=client.name, status=contract.status,
        total_kzt=contract.total_kzt, paid_kzt=_paid_sum(db, contract.id), discount_pct=contract.discount_pct,
        created_at=contract.created_at, signed_at=contract.signed_at, next_due=pending[0].due_date if pending else None,
        overdue=contract.status == ContractStatus.active and any(i.status == InstallmentStatus.overdue or i.due_date < today for i in pending),
    )


def _visible_contract(db: Session, contract_id: int, user: User) -> tuple[Contract, Client]:
    row = _scope(db.query(Contract, Client).join(Client, Contract.client_id == Client.id), user).filter(Contract.id == contract_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return row


@router.get("/contracts", response_model=ContractPage)
def list_contracts(
    status_: ContractStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=100),
    overdue: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(ANY_ROLE),
):
    today = date.today()
    query = _scope(db.query(Contract, Client).join(Client, Contract.client_id == Client.id), user)
    if status_ is not None:
        query = query.filter(Contract.status == status_)
    if q:
        like = f"%{q}%"
        query = query.filter(Contract.number.ilike(like) | Client.name.ilike(like))
    if overdue:
        late = db.query(Installment.contract_id).filter(_overdue_filter(today))
        query = query.filter(Contract.id.in_(late), Contract.status == ContractStatus.active)
    total = query.count()
    rows = query.order_by(Contract.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ContractPage(items=[_contract_row(db, c, cl, today) for c, cl in rows], total=total, page=page, page_size=page_size)


@router.get("/contracts/{contract_id}", response_model=ContractDetail)
def contract_detail(contract_id: int, db: Session = Depends(get_db), user: User = Depends(ANY_ROLE)):
    today = date.today()
    contract, client = _visible_contract(db, contract_id, user)
    installments = db.query(Installment).filter(Installment.contract_id == contract.id).order_by(Installment.seq).all()
    pays = (db.query(Payment, Contract, Client).join(Contract, Payment.contract_id == Contract.id).join(Client, Contract.client_id == Client.id)
            .filter(Payment.contract_id == contract.id).order_by(Payment.created_at.desc()).all())
    enrollments = (db.query(Enrollment, Course).join(Course, Enrollment.course_id == Course.id)
                   .filter(Enrollment.contract_id == contract.id).all())
    return ContractDetail(
        **_contract_row(db, contract, client, today).model_dump(),
        installments=[InstallmentRow(id=i.id, seq=i.seq, due_date=i.due_date, amount_kzt=i.amount_kzt, status=i.status,
                                     overdue=i.status == InstallmentStatus.overdue or (i.status == InstallmentStatus.scheduled and i.due_date < today))
                      for i in installments],
        payments=_payment_rows(pays),
        enrollments=[EnrollmentRow(id=e.id, course_code=c.code, course_title=c.title, price_kzt=e.price_kzt, discount_pct=e.discount_pct)
                     for e, c in enrollments],
    )


@router.post("/contracts/{contract_id}/sign", response_model=ContractDetail)
def sign_contract(contract_id: int, db: Session = Depends(get_db), user: User = Depends(WRITE_ROLE)):
    contract, _ = _visible_contract(db, contract_id, user)
    if contract.status != ContractStatus.draft:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a draft contract can be signed")
    contract.status = ContractStatus.active
    contract.signed_at = utcnow()
    db.commit()
    return contract_detail(contract_id, db, user)


class DeskPaymentIn(BaseModel):
    amount_kzt: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: Literal["cash", "kaspi", "card"] = "cash"


@router.post("/contracts/{contract_id}/payments", response_model=ContractDetail, status_code=status.HTTP_201_CREATED)
def take_payment(contract_id: int, payload: DeskPaymentIn, db: Session = Depends(get_db), user: User = Depends(WRITE_ROLE)):
    """A payment taken at the desk; it settles the earliest open installments it fully covers."""
    contract, _ = _visible_contract(db, contract_id, user)
    if contract.status != ContractStatus.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payments are taken on active contracts only")
    try:
        payment_service.record_payment(db, contract_id=contract.id, amount_kzt=payload.amount_kzt,
                                       external_id=f"desk-{payload.method}-{uuid.uuid4().hex[:16]}")
    except CommerceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    remaining = payload.amount_kzt
    open_rows = (db.query(Installment).filter(Installment.contract_id == contract.id,
                                               Installment.status.in_([InstallmentStatus.scheduled, InstallmentStatus.overdue]))
                 .order_by(Installment.seq).all())
    for row in open_rows:
        if remaining < row.amount_kzt:
            break
        row.status = InstallmentStatus.paid
        remaining -= row.amount_kzt
    if _paid_sum(db, contract.id) >= contract.total_kzt:
        contract.status = ContractStatus.completed
    db.commit()
    return contract_detail(contract_id, db, user)


# ---------------------------------------------------------------------------------------------------- payments
class PaymentPage(BaseModel):
    items: list[PaymentRow]
    total: int
    page: int
    page_size: int
    sum_kzt: Decimal


@router.get("/payments", response_model=PaymentPage)
def list_payments(
    status_: PaymentStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(ANY_ROLE),
):
    query = _scope(db.query(Payment, Contract, Client).join(Contract, Payment.contract_id == Contract.id)
                   .join(Client, Contract.client_id == Client.id), user)
    if status_ is not None:
        query = query.filter(Payment.status == status_)
    if q:
        like = f"%{q}%"
        query = query.filter(Contract.number.ilike(like) | Client.name.ilike(like))
    total = query.count()
    total_sum = query.with_entities(func.coalesce(func.sum(Payment.amount_kzt), 0)).scalar()
    rows = query.order_by(Payment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaymentPage(items=_payment_rows(rows), total=total, page=page, page_size=page_size, sum_kzt=Decimal(total_sum))
