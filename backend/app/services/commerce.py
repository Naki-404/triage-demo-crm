"""Bilim Academy commerce: courses, packages, enrollments, contracts, installments, payments."""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from xml.etree import ElementTree as ET

from sqlalchemy.orm import Session

from .. import faults, vulns
from ..config import settings
from ..models import (
    Contract,
    ContractStatus,
    Course,
    Enrollment,
    Installment,
    InstallmentStatus,
    Package,
    Payment,
    PaymentStatus,
    User,
    UserRole,
    utcnow,
)

TWOPLACES = Decimal("0.01")


class CommerceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def list_courses(db: Session, *, active_only: bool = True) -> list[Course]:
    q = db.query(Course)
    if active_only:
        q = q.filter(Course.is_active.is_(True))
    return q.order_by(Course.code).all()


def list_packages(db: Session, *, active_only: bool = True) -> list[Package]:
    q = db.query(Package)
    if active_only:
        q = q.filter(Package.is_active.is_(True))
    return q.order_by(Package.code).all()


def _apply_discount(price: Decimal, discount_pct: int) -> Decimal:
    if discount_pct < 0 or discount_pct > 100:
        raise CommerceError("discount_pct out of range", 422)
    factor = Decimal(100 - discount_pct) / Decimal(100)
    return (price * factor).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def check_discount_allowed(user: User, discount_pct: int) -> None:
    limit = 100 if user.role == UserRole.admin else user.max_discount_pct
    if discount_pct > limit:
        raise CommerceError(f"Discount {discount_pct}% exceeds your limit {limit}%", 403)


def enroll(
    db: Session,
    user: User,
    *,
    client_id: int,
    course_id: int | None = None,
    package_id: int | None = None,
    discount_pct: int = 0,
    price_override: Decimal | None = None,
    contract_id: int | None = None,
) -> list[Enrollment]:
    check_discount_allowed(user, discount_pct)
    created: list[Enrollment] = []

    def _one(cid: int, base: Decimal, pkg: int | None) -> Enrollment:
        existing = db.query(Enrollment).filter(Enrollment.client_id == client_id, Enrollment.course_id == cid).first()
        if existing and not faults.duplicate_enrollment_allowed():
            raise CommerceError("Already enrolled in this course", 409)
        price = price_override if vulns.price_tampering() and price_override is not None else base
        pct = discount_pct
        # FAULT_DISCOUNT_STACK: apply discount twice on package enrollments.
        if faults.discount_stacks() and pkg is not None and discount_pct > 0:
            price = _apply_discount(_apply_discount(price, pct), pct)
        else:
            price = _apply_discount(price, pct)
        row = Enrollment(
            client_id=client_id,
            course_id=cid,
            contract_id=contract_id,
            package_id=pkg,
            price_kzt=price,
            discount_pct=pct,
        )
        db.add(row)
        created.append(row)
        return row

    if package_id:
        pkg = db.get(Package, package_id)
        if pkg is None or not pkg.is_active:
            raise CommerceError("Package not found", 404)
        for item in pkg.items:
            _one(item.course_id, pkg.price_kzt / max(len(pkg.items), 1), package_id)
    elif course_id:
        course = db.get(Course, course_id)
        if course is None or not course.is_active:
            raise CommerceError("Course not found", 404)
        _one(course_id, course.price_kzt, None)
    else:
        raise CommerceError("Provide course_id or package_id", 400)

    db.commit()
    for row in created:
        db.refresh(row)
    return created


def create_contract(
    db: Session,
    *,
    client_id: int,
    number: str,
    enrollment_ids: list[int],
    discount_pct: int = 0,
    user: User,
) -> Contract:
    check_discount_allowed(user, discount_pct)
    if db.query(Contract).filter(Contract.number == number).first():
        raise CommerceError("Contract number already exists", 409)
    enrollments = db.query(Enrollment).filter(Enrollment.id.in_(enrollment_ids), Enrollment.client_id == client_id).all()
    if len(enrollments) != len(enrollment_ids):
        raise CommerceError("Enrollment mismatch", 400)
    total = sum((e.price_kzt for e in enrollments), Decimal("0"))
    if discount_pct and not faults.discount_stacks():
        total = _apply_discount(total, discount_pct)
    elif discount_pct and faults.discount_stacks():
        total = _apply_discount(_apply_discount(total, discount_pct), discount_pct)
    contract = Contract(
        number=number,
        client_id=client_id,
        status=ContractStatus.active,
        total_kzt=total.quantize(TWOPLACES),
        discount_pct=discount_pct,
        signed_at=utcnow(),
    )
    db.add(contract)
    db.flush()
    for e in enrollments:
        e.contract_id = contract.id
    db.commit()
    db.refresh(contract)
    return contract


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
        # Bug: floor each payment; last payment does not absorb remainder.
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
        # Force stale-timestamp treatment even for fresh webhooks (data_infra demo).
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
    existing = db.query(Payment).filter(Payment.external_id == external_id).first()
    if existing:
        return existing
    payment = Payment(
        contract_id=contract_id,
        amount_kzt=amount_kzt,
        status=PaymentStatus.paid,
        card_token=card_token,
        card_last4=card_last4,
        external_id=external_id,
        paid_at=utcnow(),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def export_1c_xml(db: Session, contract_id: int) -> bytes:
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise CommerceError("Contract not found", 404)
    root = ET.Element("Document", {"xmlns": "urn:1c:bilim"})
    ET.SubElement(root, "Number").text = contract.number
    ET.SubElement(root, "ClientId").text = str(contract.client_id)
    ET.SubElement(root, "Total").text = str(contract.total_kzt)
    ET.SubElement(root, "Status").text = contract.status.value
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def import_1c_xml(db: Session, raw: bytes) -> dict:
    """Parse 1C XML. When VULN_XXE_1C_IMPORT is on, external entities are resolved (intentional)."""
    if vulns.xxe_1c_import():
        # VULN_XXE_1C_IMPORT intentional, experiment only
        parser = ET.XMLParser()
        # stdlib ElementTree does not expand external entities by default in modern Python;
        # simulate vulnerable behaviour by reading SYSTEM entities manually if present.
        text = raw.decode("utf-8", errors="replace")
        if "SYSTEM" in text and "file://" in text.lower():
            raise CommerceError("XXE payload accepted (vuln demo)", 500)
        root = ET.fromstring(raw, parser=parser)
    else:
        # Hardened: forbid DOCTYPE
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise CommerceError("XML with DOCTYPE/ENTITY is not allowed", 400)
        root = ET.fromstring(raw)
    number = root.findtext("Number") or root.findtext(".//{urn:1c:bilim}Number")
    return {"number": number, "ok": True}
