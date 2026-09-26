"""Target host safety for the CRM load / attack simulator."""
from __future__ import annotations

from urllib.parse import urlparse

ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "crm.csip.dev"})
ALLOWED_SUFFIXES = (".local",)


class TargetNotAllowedError(SystemExit):
    """Raised (as SystemExit) when the target host is outside the whitelist."""


def host_allowed(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.lower().rstrip(".")
    if host in ALLOWED_HOSTS:
        return True
    return any(host.endswith(suf) for suf in ALLOWED_SUFFIXES)


def assert_target_allowed(base_url: str, *, i_own_this_target: bool) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        raise TargetNotAllowedError(f"Refusing non-http(s) target: {base_url!r}")
    host = parsed.hostname
    if host_allowed(host):
        return
    if i_own_this_target:
        return
    raise TargetNotAllowedError(
        f"Target host {host!r} is not whitelisted. "
        f"Allowed: {sorted(ALLOWED_HOSTS)} and *{ALLOWED_SUFFIXES}. "
        f"Pass --i-own-this-target only for a system you operate."
    )
