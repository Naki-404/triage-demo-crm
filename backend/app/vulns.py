"""Intentional vulnerability switches. Default off; only when CRM_MODE=vuln (or experiment+flag).

# VULN_* intentional, experiment only — isolated from clean product paths.
This module is excluded from the CSIP code-graph index (same policy as faults.py).
"""
from .config import settings

_VULN_KEYS = (
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


def active(name: str) -> bool:
    if not settings.is_vuln:
        return False
    return bool(getattr(settings, name, False))


def sqli_search() -> bool:
    return active("VULN_SQLI_SEARCH")


def idor_customer() -> bool:
    return active("VULN_IDOR_CUSTOMER")


def mass_assignment() -> bool:
    return active("VULN_MASS_ASSIGNMENT")


def stored_xss_notes() -> bool:
    return active("VULN_STORED_XSS_NOTES")


def path_traversal_export() -> bool:
    return active("VULN_PATH_TRAVERSAL_EXPORT")


def ssrf_webhook() -> bool:
    return active("VULN_SSRF_WEBHOOK")


def xxe_1c_import() -> bool:
    return active("VULN_XXE_1C_IMPORT")


def no_rate_limit_login() -> bool:
    return active("VULN_NO_RATE_LIMIT_LOGIN")


def open_redirect() -> bool:
    return active("VULN_OPEN_REDIRECT")


def csv_injection() -> bool:
    return active("VULN_CSV_INJECTION")


def price_tampering() -> bool:
    return active("VULN_PRICE_TAMPERING")


def payment_signature_skip() -> bool:
    return active("VULN_PAYMENT_SIGNATURE")


def snapshot() -> dict[str, bool | str]:
    return {"crm_mode": settings.CRM_MODE, **{k: active(k) for k in _VULN_KEYS}}


def all_keys() -> tuple[str, ...]:
    return _VULN_KEYS
