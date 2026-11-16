"""Application events for the log and for Sentry.

`emit()` is the one place a business event (a 4xx with a reason, a refused login, a note, a suspicious header)
becomes an ECS line and, for warning/error, a Sentry message. The request id is the join key with the access log,
so the triage platform sees the error and the request it belongs to as one incident.
"""
from __future__ import annotations

import logging
import re
from contextvars import ContextVar
from typing import Any

import sentry_sdk
from starlette.requests import Request

logger = logging.getLogger("crm.observe")

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")
_IIN_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_SECRET_FIELD_RE = re.compile(r'("(?:password|token|secret|card_token|signature)"\s*:\s*")(?:[^"\\]|\\.)*(")', re.IGNORECASE)
MAX_BODY_CHARS = 2000

# Fields attached to the ECS line of the current request by emit() (merged by the middleware).
request_fields: ContextVar[dict[str, Any] | None] = ContextVar("request_fields", default=None)


def mask_text(text: str) -> str:
    """Personal data never reaches the log or Sentry in clear: IIN, phone, e-mail and secret fields are masked."""
    text = _SECRET_FIELD_RE.sub(r"\1***\2", text)
    text = _IIN_RE.sub("[iin]", text)
    text = _EMAIL_RE.sub("[email]", text)
    text = _PHONE_RE.sub("[phone]", text)
    return text[:MAX_BODY_CHARS]


def valid_request_id(value: str | None) -> str | None:
    """A client-supplied request id is kept only when it is a short plain token (no log forging, no 4 KB headers)."""
    if value and REQUEST_ID_RE.match(value):
        return value
    return None


def emit(action: str, level: str, message: str, request: Request | None = None, **extra: Any) -> None:
    """Record an application event: ECS fields for the request line plus a Sentry message for warning/error."""
    fields: dict[str, Any] = {"event.action": action, "event.outcome": "failure" if level in ("warning", "error") else "success"}
    if level in ("warning", "error"):
        # a request that answered 2xx but met something worth a warning (hostile input) logs at that level, so log
        # consumers filtering on warning/error (CSIP) see it
        fields["log.level"] = level
    if message:
        fields["error.message" if level in ("warning", "error") else "message"] = mask_text(message)
    for key, value in extra.items():
        if value is not None:
            # ECS names: log consumers (CSIP polls error.type) read the dotted field
            fields["error.type" if key == "error_type" else key] = value
    current = request_fields.get()
    if current is not None:
        current.update(fields)
    if level in ("warning", "error") and sentry_sdk.is_initialized():
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("event.action", action)
            for key, value in extra.items():
                if value is not None:
                    scope.set_extra(key, value)
            if request is not None:
                scope.set_tag("http.method", request.method)
                scope.set_extra("url.path", request.url.path)
            sentry_sdk.capture_message(f"{action}: {mask_text(message)}", level=level)
    logger.log(logging.WARNING if level in ("warning", "error") else logging.INFO, "%s: %s", action, mask_text(message))


SUSPICIOUS_MARKERS = ("ignore previous", "ignore all", "system prompt", "<script", "${jndi", "../", "sleep(")
# how much of a suspicious value goes into the warning (masked): enough for a reader to see what it tried
SUSPICIOUS_SAMPLE = 300


def looks_suspicious(text: str | None) -> bool:
    """Text that reads like instructions or an injection aimed at whoever (or whatever) reads the logs."""
    low = (text or "").lower()
    return any(marker in low for marker in SUSPICIOUS_MARKERS)


def suspicious_headers(request: Request) -> list[str]:
    """Header names whose values look like instructions or injections aimed at a log reader."""
    return [
        name
        for name, value in request.headers.items()
        if name.lower() not in ("cookie", "authorization") and looks_suspicious(value)
    ]


def report_suspicious(where: str, text: str, request: Request | None = None, **extra: Any) -> None:
    """Raise input that looks like instructions to a warning (log line and Sentry), masked and cut short, so the
    downstream reader (a triage platform, a model) sees it as an attack attempt instead of trusting it."""
    emit("suspicious_input", "warning", f"{where}: {text[:SUSPICIOUS_SAMPLE]}", request, **extra)
