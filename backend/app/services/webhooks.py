"""Outbound webhook for a manager's profile (CRM pings it when a client card changes).

Clean mode resolves the host first and only talks to public addresses over http(s) without following redirects.
The stand switch for this module skips the checks and returns the upstream body.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from .. import vulns
from ..errors import DomainError

MAX_PREVIEW = 200
TIMEOUT_SECONDS = 3.0


class WebhookError(DomainError):
    status_code = 400


def _resolve_public(host: str) -> str:
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise WebhookError("webhook host does not resolve") from exc
    addresses = {ipaddress.ip_address(info[4][0]) for info in infos}
    if not addresses or any(not ip.is_global for ip in addresses):
        raise WebhookError("webhook host must resolve to a public address")
    return str(sorted(addresses, key=str)[0])


def validate_webhook_url(url: str) -> str:
    """The URL a profile may store: http(s), a host name, no credentials, resolving to a public address."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise WebhookError("webhook URL must be http(s) with a host")
    if parsed.username or parsed.password:
        raise WebhookError("webhook URL must not carry credentials")
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        raise WebhookError("webhook URL must use a host name, not an IP address")
    _resolve_public(parsed.hostname)
    return parsed.geturl()


def send_test(url: str) -> dict:
    """Fire a test GET at the webhook and report the status (with a body preview when the checks are off)."""
    if vulns.ssrf_webhook():
        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
                res = client.get(url)
        except httpx.HTTPError as exc:
            raise WebhookError(f"webhook unreachable: {type(exc).__name__}", 502) from exc
        return {"status_code": res.status_code, "preview": res.text[:MAX_PREVIEW]}
    clean = validate_webhook_url(url)
    parsed = urlparse(clean)
    pinned_ip = _resolve_public(parsed.hostname or "")
    if parsed.scheme == "https":
        # TLS needs the real name for SNI and certificate checks; httpx re-resolves, so check again right after
        target, headers = clean, {"User-Agent": "qazaq-crm-webhook"}
    else:
        # plain http: talk to the checked address and send the name in Host, so a DNS rebind cannot redirect us
        host = f"[{pinned_ip}]" if ":" in pinned_ip else pinned_ip
        netloc = f"{host}:{parsed.port}" if parsed.port else host
        target = parsed._replace(netloc=netloc).geturl()
        headers = {"User-Agent": "qazaq-crm-webhook", "Host": parsed.netloc}
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=False) as client:
            if parsed.scheme == "https" and _resolve_public(parsed.hostname or "") != pinned_ip:
                raise WebhookError("webhook host changed its address during the check")
            res = client.get(target, headers=headers)
    except httpx.HTTPError as exc:
        raise WebhookError(f"webhook unreachable: {type(exc).__name__}", 502) from exc
    return {"status_code": res.status_code}
