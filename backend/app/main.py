import logging

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from .config import settings
from .logging_ecs import RequestContextMiddleware
from .routers import auth, customers, notes, stand
from .schemas import HealthOut

logger = logging.getLogger("crm")


def _init_sentry() -> None:
    dsn = (settings.SENTRY_DSN or "").strip()
    if not dsn or "://" not in dsn:
        return
    send_pii = settings.SEND_DEFAULT_PII and settings.is_experiment
    sentry_sdk.init(
        dsn=dsn,
        environment=settings.SENTRY_ENVIRONMENT,
        release=f"qazaq-crm@{settings.APP_VERSION}",
        send_default_pii=send_pii,
        traces_sample_rate=0,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )
    sentry_sdk.set_tag("service", "qazaq-crm")
    sentry_sdk.set_tag("crm_mode", settings.CRM_MODE)


def create_app() -> FastAPI:
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    _init_sentry()

    app = FastAPI(title="Qazaq CRM", version=settings.APP_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)

    @app.get("/health", response_model=HealthOut)
    def health():
        return HealthOut(status="ok", version=settings.APP_VERSION, crm_mode=settings.CRM_MODE)

    @app.get("/api/stand/public")
    def stand_public():
        """Minimal mode signal for the frontend (no auth)."""
        return {"crm_mode": settings.CRM_MODE, "stand_ui": settings.is_experiment}

    app.include_router(auth.router)
    app.include_router(customers.router)
    app.include_router(notes.router)
    app.include_router(stand.router)
    return app


app = create_app()
