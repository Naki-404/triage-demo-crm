"""Enrollment creation and listing."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from .. import faults, vulns
from ..models import Client, Course, Enrollment, Package, User
from .access import assert_can_access
from .commerce_pricing import CommerceError, apply_discount, check_discount_allowed


def list_for_client(db: Session, client_id: int) -> list[Enrollment]:
    return db.query(Enrollment).filter(Enrollment.client_id == client_id).order_by(Enrollment.id.desc()).all()


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
    client = db.get(Client, client_id)
    if client is None:
        raise CommerceError("Client not found", 404)
    assert_can_access(user, client)

    check_discount_allowed(user, discount_pct)
    created: list[Enrollment] = []

    def _one(cid: int, base: Decimal, pkg: int | None) -> Enrollment:
        existing = db.query(Enrollment).filter(Enrollment.client_id == client_id, Enrollment.course_id == cid).first()
        if existing and not faults.duplicate_enrollment_allowed():
            raise CommerceError("Already enrolled in this course", 409)
        price = price_override if vulns.price_tampering() and price_override is not None else base
        pct = discount_pct
        if faults.discount_stacks() and pkg is not None and discount_pct > 0:
            price = apply_discount(apply_discount(price, pct), pct)
        else:
            price = apply_discount(price, pct)
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
