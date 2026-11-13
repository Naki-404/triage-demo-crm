"""Stand-mode switches. Applied only when CRM_MODE=experiment.

This module is excluded from the CSIP code-graph index and from model context snippets.
It must not contain product feature logic — only flags read by service branches.
"""
from .stand_flags import FAULT_KEYS, fault_active, fault_snapshot

__all__ = ["FAULT_KEYS", "active", "snapshot"]

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


def replica_lag() -> bool:
    """When on: card reads go to a read replica that is behind the primary."""
    return active("FAULT_REPLICA_LAG")


def legacy_amount_overflow() -> bool:
    """When on: a contract imported from the legacy system carries an amount the NUMERIC(12,2) column cannot hold."""
    return active("FAULT_LEGACY_AMOUNT")


def disk_full() -> bool:
    """When on: the export volume has no free space left."""
    return active("FAULT_DISK_FULL")


def export_requires_no_contract_bug() -> bool:
    """When on: export crashes if client has no contract (KeyError / missing field)."""
    return active("FAULT_EXPORT_NO_CONTRACT")


def cache_down() -> bool:
    """When on: the shared cache cluster does not answer."""
    return active("FAULT_CACHE_DOWN")


def tax_dns_failure() -> bool:
    """When on: the tax service host name does not resolve."""
    return active("FAULT_TAX_DNS")


def tax_cert_expired() -> bool:
    """When on: the tax service TLS certificate has expired."""
    return active("FAULT_TAX_CERT")


def id_sequence_behind() -> bool:
    """When on: the clients id sequence is behind max(id) after a bulk import."""
    return active("FAULT_ID_SEQUENCE")


def fk_orphan() -> bool:
    """When on: a contract references an enrollment row lost in a partial restore."""
    return active("FAULT_FK_ORPHAN")


def broker_down() -> bool:
    """When on: the message broker refuses billing events."""
    return active("FAULT_BROKER_DOWN")


def db_read_only() -> bool:
    """When on: the database is read-only during a fail-over."""
    return active("FAULT_DB_READONLY")


def clock_skew() -> bool:
    """When on: this node's clock runs ahead of the auth node."""
    return active("FAULT_CLOCK_SKEW")
