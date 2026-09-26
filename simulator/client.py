"""HTTP client for Qazaq CRM with request-id, cookies, and simple rate limiting."""
from __future__ import annotations

import time
import uuid
from typing import Any

import httpx


class CrmClient:
    def __init__(
        self,
        base_url: str,
        *,
        username: str = "manager",
        password: str = "Manager-2026!",
        admin_username: str = "admin",
        admin_password: str = "Admin-2026!",
        min_interval_ms: float = 50.0,
        timeout: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.min_interval = min_interval_ms / 1000.0
        self._last = 0.0
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout, follow_redirects=True)
        self._authed = False

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        now = time.monotonic()
        wait = self.min_interval - (now - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def request(
        self,
        method: str,
        path: str,
        *,
        request_id: str | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        self._throttle()
        rid = request_id or uuid.uuid4().hex
        hdrs = {"X-Request-ID": rid, **(headers or {})}
        return self._client.request(method, path, headers=hdrs, **kwargs)

    def login(self, *, as_admin: bool = False) -> httpx.Response:
        user = self.admin_username if as_admin else self.username
        password = self.admin_password if as_admin else self.password
        res = self.request("POST", "/api/auth/login", json={"username": user, "password": password})
        self._authed = res.status_code == 200
        self._as_admin = as_admin and self._authed
        return res

    def ensure_login(self, *, as_admin: bool = False) -> None:
        if self._authed and getattr(self, "_as_admin", False) == as_admin:
            return
        res = self.login(as_admin=as_admin)
        if res.status_code != 200:
            raise RuntimeError(f"login failed: {res.status_code} {res.text}")

    def patch_stand(self, **flags: Any) -> httpx.Response:
        self.ensure_login(as_admin=True)
        return self.request("PATCH", "/api/stand", json=flags)

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", path, **kwargs)
