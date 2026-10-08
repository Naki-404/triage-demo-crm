"""Backward-compatible commerce facade — logic lives in domain modules."""
from __future__ import annotations

from .commerce_pricing import CommerceError, check_discount_allowed
from .catalog import list_courses, list_packages
from .contracts import create_contract, export_1c_xml, import_1c_xml
from .enrollments import enroll
from .installments import build_installment_schedule
from .payments import record_payment, verify_payment_hmac

__all__ = [
    "CommerceError",
    "build_installment_schedule",
    "check_discount_allowed",
    "create_contract",
    "enroll",
    "export_1c_xml",
    "import_1c_xml",
    "list_courses",
    "list_packages",
    "record_payment",
    "verify_payment_hmac",
]
