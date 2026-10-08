"""Stand-mode switches. Applied only when CRM_MODE=experiment.

This module is excluded from the CSIP code-graph index and from model context snippets.
It must not contain product feature logic — only flags read by service branches.
"""
from .stand_flags import FAULT_KEYS, fault_active, fault_snapshot

active = fault_active
snapshot = fault_snapshot


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
