"""Infrastructure and stored-data failures for the experiment stand (FAULT_* switches, CRM_MODE=experiment only).

Each one is a failure outside the CRM's own logic: a dependency, the network, the clock, the database state.
The message is what the real component would report, so the event alone shows where the problem is.
"""
from __future__ import annotations

import random

from .. import faults
from ..errors import DomainError, UnavailableError


class CacheUnavailableError(UnavailableError):
    """The shared cache cluster does not answer."""


class IdSequenceError(DomainError):
    """The primary-key sequence is behind max(id) after a bulk import."""

    status_code = 500


class OrphanRowError(DomainError):
    """A stored row references a row that no longer exists."""

    status_code = 500


class BrokerUnavailableError(UnavailableError):
    """The message broker refused the event."""


class ReadOnlyDatabaseError(UnavailableError):
    """The database accepts reads only (fail-over in progress)."""


def check_cache() -> None:
    if faults.cache_down():
        node = random.choice(["redis-0", "redis-1", "cache-main", "valkey-0"])
        raise CacheUnavailableError(f"cache cluster {node}:6379 unreachable: Connection refused (course price cache)")


def tax_network_error() -> str | None:
    """The message a failed connection to the tax service would carry, or None."""
    host = random.choice(["tax-api.kgd.gov.kz", "esf.gov.kz", "api.kgd.kz"])
    if faults.tax_dns_failure():
        return f"tax service unavailable: [Errno -3] Temporary failure in name resolution: '{host}'"
    if faults.tax_cert_expired():
        return f"tax service unavailable: SSL: CERTIFICATE_VERIFY_FAILED certificate verify failed: certificate has expired ({host})"
    return None


def check_id_sequence(table: str) -> None:
    if faults.id_sequence_behind():
        taken = random.randint(1200, 98000)
        raise IdSequenceError(f'duplicate key value violates unique constraint "{table}_pkey": Key (id)=({taken}) already exists; '
                              f"sequence {table}_id_seq is behind max(id) after the bulk import")


def check_orphans(contract_number: str) -> None:
    if faults.fk_orphan():
        missing = random.randint(100, 9000)
        raise OrphanRowError(f"contract {contract_number}: enrollment_id={missing} does not exist in enrollments "
                             "(row missing after a partial restore); contract list cannot be built")


def check_broker() -> None:
    if faults.broker_down():
        node = random.choice(["rabbitmq-0", "rabbitmq-1", "mq-main"])
        raise BrokerUnavailableError(f"message broker {node}: channel closed (queue billing.events reached max-length 50000); "
                                     "installment schedule event not published")


def check_writable() -> None:
    if faults.db_read_only():
        primary, standby = random.choice([("pg-0", "pg-1"), ("db-primary", "db-standby"), ("pg-main", "pg-ro-1")])
        raise ReadOnlyDatabaseError(f"cannot execute INSERT in a read-only transaction: primary {primary} failed over, "
                                    f"{standby} is still in recovery")


def clock_skew_detail() -> str | None:
    if faults.clock_skew():
        return (f"session token rejected: issued {random.randint(90, 900)} s in the future — "
                "this node's clock is ahead of the auth node (NTP not synchronised)")
    return None
