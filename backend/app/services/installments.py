"""Installment schedules."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from .. import faults
from ..models import Contract, Installment
from .commerce_pricing import TWOPLACES, CommerceError


def list_for_contract(db: Session, contract_id: int) -> list[Installment]:
    return db.query(Installment).filter(Installment.contract_id == contract_id).order_by(Installment.seq).all()


def build_installment_schedule(
    db: Session,
    contract: Contract,
    *,
    months: int,
    first_due: date | None = None,
) -> list[Installment]:
    if months not in (3, 6, 12):
        raise CommerceError("Installment term must be 3, 6 or 12 months", 422)
    first_due = first_due or (date.today() + timedelta(days=30))
    total = Decimal(contract.total_kzt)
    if faults.installment_rounding_bug():
        each = (total / months).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        amounts = [each] * months
    else:
        each = (total / months).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        amounts = [each] * (months - 1)
        amounts.append((total - each * (months - 1)).quantize(TWOPLACES))
    rows: list[Installment] = []
    for i, amount in enumerate(amounts, start=1):
        due = first_due + timedelta(days=30 * (i - 1))
        row = Installment(contract_id=contract.id, seq=i, due_date=due, amount_kzt=amount)
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows
