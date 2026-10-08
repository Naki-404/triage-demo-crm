"""Shared stand flag keys and activation helpers for faults.py and vulns.py."""
from __future__ import annotations

from .config import settings

FAULT_KEYS: tuple[str, ...] = (
    "FAULT_IIN_SECOND_WEIGHTS",
    "FAULT_NAME_SEARCH_RAW_SQL",
    "FAULT_EXPORT_EMPTY_FIELD",
    "FAULT_CORRUPT_RECORD",
    "FAULT_TAX_TIMEOUT",
    "FAULT_NOTES_DOWN",
    "FAULT_POOL_EXHAUSTED",
    "FAULT_PAYMENT_WEBHOOK",
    "FAULT_DISCOUNT_STACK",
    "FAULT_DUPLICATE_ENROLLMENT",
    "FAULT_INSTALLMENT_ROUNDING",
    "FAULT_EXPORT_NO_CONTRACT",
)

VULN_KEYS: tuple[str, ...] = (
    "VULN_SQLI_SEARCH",
    "VULN_IDOR_CUSTOMER",
    "VULN_MASS_ASSIGNMENT",
    "VULN_STORED_XSS_NOTES",
    "VULN_PATH_TRAVERSAL_EXPORT",
    "VULN_SSRF_WEBHOOK",
    "VULN_XXE_1C_IMPORT",
    "VULN_NO_RATE_LIMIT_LOGIN",
    "VULN_OPEN_REDIRECT",
    "VULN_CSV_INJECTION",
    "VULN_PRICE_TAMPERING",
    "VULN_PAYMENT_SIGNATURE",
)


def fault_active(name: str) -> bool:
    if not settings.is_experiment:
        return False
    return bool(getattr(settings, name, False))


def vuln_active(name: str) -> bool:
    if not settings.is_vuln:
        return False
    return bool(getattr(settings, name, False))


def fault_snapshot() -> dict[str, bool | str]:
    return {"crm_mode": settings.CRM_MODE, **{k: fault_active(k) for k in FAULT_KEYS}}


def vuln_snapshot() -> dict[str, bool | str]:
    return {"crm_mode": settings.CRM_MODE, **{k: vuln_active(k) for k in VULN_KEYS}}
