"""Shared commerce pricing helpers."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from ..models import User, UserRole

TWOPLACES = Decimal("0.01")


class CommerceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def apply_discount(price: Decimal, discount_pct: int) -> Decimal:
    if discount_pct < 0 or discount_pct > 100:
        raise CommerceError("discount_pct out of range", 422)
    factor = Decimal(100 - discount_pct) / Decimal(100)
    return (price * factor).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def check_discount_allowed(user: User, discount_pct: int) -> None:
    limit = 100 if user.role == UserRole.admin else user.max_discount_pct
    if discount_pct > limit:
        raise CommerceError(f"Discount {discount_pct}% exceeds your limit {limit}%", 403)
