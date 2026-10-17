"""Domain errors and the one handler that turns them into HTTP responses.

Services raise a DomainError subclass with the status it means; routers may still catch specific errors to add
context, but anything that slips through lands here instead of becoming a 500 with the exception text in it.
"""
from __future__ import annotations

import logging

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from .observe import emit

logger = logging.getLogger("crm.errors")


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str = "", status_code: int | None = None):
        super().__init__(message or self.__class__.__name__)
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class UnavailableError(DomainError):
    status_code = 503


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError):
        if exc.status_code >= 500:
            # a server-side failure keeps its traceback in Sentry (the warning below only adds the business context)
            sentry_sdk.capture_exception(exc)
        emit("domain_error", "warning", str(exc), request, status_code=exc.status_code, error_type=type(exc).__name__)
        return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

    @app.exception_handler(IntegrityError)
    async def _integrity(request: Request, exc: IntegrityError):
        # Two requests raced for the same unique row; the client retries, the constraint name stays in the log.
        logger.warning("integrity error on %s %s: %s", request.method, request.url.path, type(exc.orig).__name__)
        emit("integrity_conflict", "warning", "conflicting write", request, status_code=409)
        return JSONResponse({"detail": "Conflicting write, retry"}, status_code=409)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        emit("validation_error", "info", "request validation failed", request, status_code=422)
        return JSONResponse({"detail": exc.errors()}, status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # The traceback goes to the log and to Sentry; the client gets a generic body (no exception text).
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        sentry_sdk.capture_exception(exc)
        emit("unhandled_error", "error", type(exc).__name__, request, status_code=500, error_type=type(exc).__name__)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
