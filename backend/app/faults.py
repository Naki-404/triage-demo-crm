"""Stand-mode switches. Applied only when CRM_MODE=experiment.

This module is excluded from the CSIP code-graph index and from model context snippets.
It must not contain product feature logic — only flags read by service branches.
"""
from .config import settings

FAULT_KEYS = (
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
    }
