"""ECS-oriented request logging with pluggable shippers (file / elasticsearch / null)."""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
import uuid
from abc import ABC, abstractmethod
from contextvars import ContextVar
from pathlib import Path
from typing import Any

import httpx
import sentry_sdk
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import settings
from .models import utcnow
from .observe import mask_text, request_fields, suspicious_headers, valid_request_id

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger("crm.ecs")


class LogShipper(ABC):
    @abstractmethod
    def ship(self, event: dict[str, Any]) -> None: ...


class NullShipper(LogShipper):
    def ship(self, event: dict[str, Any]) -> None:
        return


class FileShipper(LogShipper):
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def ship(self, event: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


class ElasticsearchBulkShipper(LogShipper):
    """Bulk sender on a background thread: a request only puts its log line on a bounded queue, so a slow or
    unreachable Elasticsearch never delays the CRM. Lines are sent in batches every FLUSH_SECONDS; when the
    queue is full the newest line is dropped and counted (logs must not take the application down)."""

    FLUSH_SECONDS = 1.0
    BATCH = 500
    QUEUE_MAX = 10_000

    def __init__(self, url: str, index: str):
        self.url = url.rstrip("/")
        self.index = index
        self._client = httpx.Client(timeout=5.0)
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=self.QUEUE_MAX)
        self.dropped = 0
        threading.Thread(target=self._run, name="es-shipper", daemon=True).start()

    def ship(self, event: dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            self.dropped += 1

    def _run(self) -> None:
        while True:
            batch = [self._queue.get()]
            deadline = time.monotonic() + self.FLUSH_SECONDS
            while len(batch) < self.BATCH and time.monotonic() < deadline:
                try:
                    batch.append(self._queue.get(timeout=max(deadline - time.monotonic(), 0.01)))
                except queue.Empty:
                    break
            self._send(batch)

    def _send(self, batch: list[dict[str, Any]]) -> None:
        meta = json.dumps({"index": {"_index": self.index}})
        body = "".join(meta + "\n" + json.dumps(event, ensure_ascii=False) + "\n" for event in batch)
        try:
            self._client.post(f"{self.url}/_bulk", content=body, headers={"Content-Type": "application/x-ndjson"})
        except Exception:
            logger.exception("elasticsearch ship failed (%d lines)", len(batch))


def get_shipper() -> LogShipper:
    kind = (settings.LOG_SHIPPER or "null").lower()
    if kind == "file":
        return FileShipper(settings.LOG_FILE_PATH)
    if kind == "elasticsearch":
        if not settings.ELASTICSEARCH_URL:
            logger.warning("LOG_SHIPPER=elasticsearch but ELASTICSEARCH_URL is empty; using null")
            return NullShipper()
        return ElasticsearchBulkShipper(settings.ELASTICSEARCH_URL, settings.ELASTICSEARCH_INDEX)
    return NullShipper()


_shipper: LogShipper | None = None


def shipper() -> LogShipper:
    global _shipper
    if _shipper is None:
        _shipper = get_shipper()
    return _shipper


MAX_LOGGED_BODY = 8192


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = valid_request_id(request.headers.get("x-request-id")) or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        fields_token = request_fields.set({})
        sentry_sdk.set_tag("request_id", request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            event = {
                "@timestamp": utcnow().isoformat(timespec="milliseconds") + "Z",
                "trace.id": request_id,
                "http.request.method": request.method,
                "url.path": request.url.path,
                "url.query": mask_text(request.url.query) if request.url.query else None,
                "http.response.status_code": status_code,
                "event.duration": duration_ms * 1_000_000,
                "client.ip": request.client.host if request.client else None,
                "user.id": getattr(request.state, "user_id", None),
                "user_agent.original": request.headers.get("user-agent"),
                # ECS fields log consumers filter on (CSIP polls log.level error/warning)
                "log.level": "error" if status_code >= 500 else "warning" if status_code >= 400 else "info",
                "service.name": "qazaq-crm",
                "service.environment": settings.SENTRY_ENVIRONMENT,
            }
            if status_code >= 400:
                event["http.request.body.content"] = await _masked_body(request)
            odd = suspicious_headers(request)
            if odd:
                event["http.request.headers.suspicious"] = odd
            event.update(request_fields.get() or {})
            parts = (request.method, request.url.path, status_code, event.get("error.message"))
            event["message"] = " ".join(str(x) for x in parts if x)
            try:
                shipper().ship({k: v for k, v in event.items() if v is not None})
            except Exception:
                logger.exception("log ship failed")
            request_fields.reset(fields_token)
            request_id_var.reset(token)


async def _masked_body(request: Request) -> str | None:
    """The request body of a failed call, masked, for the analyst; binary and large bodies are skipped."""
    ctype = request.headers.get("content-type", "")
    if request.method not in ("POST", "PUT", "PATCH") or not ctype.startswith(("application/json", "application/xml", "text/")):
        return None
    try:
        raw = await request.body()
    except Exception:
        return None
    if not raw or len(raw) > MAX_LOGGED_BODY:
        return None
    return mask_text(raw.decode("utf-8", errors="replace"))
