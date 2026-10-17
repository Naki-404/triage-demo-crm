import logging
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from .config import production_problems, settings
from .errors import install_error_handlers
from .logging_ecs import RequestContextMiddleware
from .routers import auth, commerce, customers, notes, stand
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


def create_app() -> FastAPI:
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    problems = production_problems(settings)
    if problems:
        raise RuntimeError("refusing to start in production: " + "; ".join(problems))
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
    install_error_handlers(app)

    @app.get("/health", response_model=HealthOut)
    def health():
        return HealthOut(
            status="ok",
            version=settings.APP_VERSION,
            crm_mode="clean" if settings.is_production else settings.CRM_MODE,
            company=settings.COMPANY_NAME,
        )

    @app.get("/api/stand/public")
    def stand_public():
        """Minimal mode signal for the frontend (no auth)."""
        return {
            "stand_ui": (settings.is_experiment or settings.is_vuln) and settings.STAND_CONTROL_ENABLED and not settings.is_production,
            "company": settings.COMPANY_NAME,
        }

    app.include_router(auth.router)
    app.include_router(customers.router)
    app.include_router(notes.router)
    app.include_router(commerce.router)
    app.include_router(stand.router)
    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built SPA from STATIC_DIR when it exists (the Docker image); dev runs Vite separately."""
    static_dir = Path(settings.STATIC_DIR) if settings.STATIC_DIR else None
    if not static_dir or not (static_dir / "index.html").is_file():
        return
    from fastapi.responses import FileResponse
    from starlette.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
    index = static_dir / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = (static_dir / path).resolve()
        if path and candidate.is_file() and static_dir.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()
