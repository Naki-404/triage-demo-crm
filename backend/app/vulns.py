"""Intentional vulnerability switches. Default off; only when CRM_MODE=vuln (or experiment+flag).

# VULN_* intentional, experiment only — isolated from clean product paths.
This module is excluded from the CSIP code-graph index (same policy as faults.py).
"""
from .stand_flags import VULN_KEYS, vuln_active, vuln_snapshot

active = vuln_active
snapshot = vuln_snapshot


def all_keys() -> tuple[str, ...]:
    return VULN_KEYS


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
