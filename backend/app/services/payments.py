"""Payment webhooks and listing."""
from __future__ import annotations

import hashlib
import hmac
import time
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import faults, vulns
from ..config import settings
from ..models import Contract, Payment, PaymentStatus, utcnow
from .commerce_pricing import CommerceError


def list_for_contract(db: Session, contract_id: int) -> list[Payment]:
    return db.query(Payment).filter(Payment.contract_id == contract_id).order_by(Payment.id.desc()).all()


def verify_payment_hmac(body: bytes, signature: str, timestamp: str) -> None:
    if vulns.payment_signature_skip():
        return
    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise CommerceError("Invalid timestamp", 400) from exc
    age = abs(int(time.time()) - ts)
    max_age = settings.PAYMENT_WEBHOOK_MAX_AGE_SECONDS
    if faults.payment_webhook_stale():
        raise CommerceError("Webhook timestamp expired", 400)
    if age > max_age:
        raise CommerceError("Webhook timestamp expired", 400)
    expected = hmac.new(settings.PAYMENT_WEBHOOK_SECRET.encode(), body + timestamp.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ""):
        raise CommerceError("Invalid payment signature", 401)


def record_payment(
    db: Session,
    *,
    contract_id: int,
    amount_kzt: Decimal,
    external_id: str,
    card_token: str | None = None,
    card_last4: str | None = None,
) -> Payment:
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise CommerceError("Contract not found", 404)
    if amount_kzt is None or amount_kzt <= 0:
        raise CommerceError("Payment amount must be positive", 400)
    if contract.total_kzt is not None and amount_kzt > contract.total_kzt:
        raise CommerceError("Payment exceeds the contract total", 400)
    existing = db.query(Payment).filter(Payment.external_id == external_id).first()
    if existing:
        return existing
    paid = db.query(func.coalesce(func.sum(Payment.amount_kzt), 0)).filter(Payment.contract_id == contract_id).scalar()
    if contract.total_kzt is not None and Decimal(paid) + amount_kzt > contract.total_kzt:
        raise CommerceError("Payments would exceed the contract total", 400)
    payment = Payment(
        contract_id=contract_id,
        amount_kzt=amount_kzt,
        status=PaymentStatus.paid,
        card_token=None,  # the gateway token is never stored; the last four digits are enough for support
        card_last4=card_last4,
        external_id=external_id,
        paid_at=utcnow(),
    )
    db.add(payment)
    try:
        db.commit()
    except IntegrityError:
        # the same webhook delivered twice at once: the other request already stored it
        db.rollback()
        return db.query(Payment).filter(Payment.external_id == external_id).one()
    db.refresh(payment)
    return payment
