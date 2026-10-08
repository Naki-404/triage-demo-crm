"""Course and package catalog reads."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Course, Package


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
