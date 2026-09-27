"""Stand-mode switches. Applied only when CRM_MODE=experiment.

This module is excluded from the CSIP code-graph index and from model context snippets.
It must not contain product feature logic — only flags read by service branches.
"""
from .config import settings


def active(name: str) -> bool:
    if not settings.is_experiment:
        return False
    return bool(getattr(settings, name, False))


def iin_skips_second_weights() -> bool:
    return active("FAULT_IIN_SECOND_WEIGHTS")


def name_search_uses_raw_sql() -> bool:
    return active("FAULT_NAME_SEARCH_RAW_SQL")


def export_fails_on_empty_field() -> bool:
    return active("FAULT_EXPORT_EMPTY_FIELD")


def corrupt_record_enabled() -> bool:
    return active("FAULT_CORRUPT_RECORD")


def tax_times_out() -> bool:
    return active("FAULT_TAX_TIMEOUT")


def notes_unavailable() -> bool:
    return active("FAULT_NOTES_DOWN")


def pool_exhausted() -> bool:
    return active("FAULT_POOL_EXHAUSTED")


def payment_webhook_stale() -> bool:
    return active("FAULT_PAYMENT_WEBHOOK")


def discount_stacks() -> bool:
    return active("FAULT_DISCOUNT_STACK")


def duplicate_enrollment_allowed() -> bool:
    return active("FAULT_DUPLICATE_ENROLLMENT")


def installment_rounding_bug() -> bool:
    return active("FAULT_INSTALLMENT_ROUNDING")


def export_requires_no_contract_bug() -> bool:
    """When on: export crashes if client has no contract (KeyError / missing field)."""
    return active("FAULT_EXPORT_NO_CONTRACT")


def snapshot() -> dict[str, bool | str]:
    return {
        "crm_mode": settings.CRM_MODE,
        "FAULT_IIN_SECOND_WEIGHTS": iin_skips_second_weights(),
        "FAULT_NAME_SEARCH_RAW_SQL": name_search_uses_raw_sql(),
        "FAULT_EXPORT_EMPTY_FIELD": export_fails_on_empty_field(),
        "FAULT_CORRUPT_RECORD": corrupt_record_enabled(),
        "FAULT_TAX_TIMEOUT": tax_times_out(),
        "FAULT_NOTES_DOWN": notes_unavailable(),
        "FAULT_POOL_EXHAUSTED": pool_exhausted(),
        "FAULT_PAYMENT_WEBHOOK": payment_webhook_stale(),
        "FAULT_DISCOUNT_STACK": discount_stacks(),
        "FAULT_DUPLICATE_ENROLLMENT": duplicate_enrollment_allowed(),
        "FAULT_INSTALLMENT_ROUNDING": installment_rounding_bug(),
        "FAULT_EXPORT_NO_CONTRACT": export_requires_no_contract_bug(),
        **{k: bool(getattr(settings, k, False)) and settings.is_vuln for k in _VULN_KEYS},
    }


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
