"""ECS-oriented request logging with pluggable shippers (file / elasticsearch / null)."""
from __future__ import annotations

import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from contextvars import ContextVar
from pathlib import Path
from typing import Any

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import settings
from .models import utcnow

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
    """Minimal bulk sender. Hosting (VPS vs Elastic Cloud) is configured via ELASTICSEARCH_URL."""

    def __init__(self, url: str, index: str):
        self.url = url.rstrip("/")
        self.index = index
        self._client = httpx.Client(timeout=5.0)

    def ship(self, event: dict[str, Any]) -> None:
        meta = json.dumps({"index": {"_index": self.index}})
        body = meta + "\n" + json.dumps(event, ensure_ascii=False) + "\n"
        try:
            self._client.post(f"{self.url}/_bulk", content=body, headers={"Content-Type": "application/x-ndjson"})
        except Exception:
            logger.exception("elasticsearch ship failed")


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


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(request_id)
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
                "http.response.status_code": status_code,
                "event.duration": duration_ms * 1_000_000,
                "client.ip": request.client.host if request.client else None,
                "user.id": getattr(request.state, "user_id", None),
            }
            try:
                shipper().ship(event)
            except Exception:
                logger.exception("log ship failed")
            request_id_var.reset(token)
