from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    CRM_MODE: str = "clean"  # clean | experiment
    SECRET_KEY: str = "change-me"
    COOKIE_SECURE: bool = False
    SESSION_EXPIRE_HOURS: int = 24
    CORS_ORIGINS: str = "http://localhost:5174,http://127.0.0.1:5174"
    BASE_URL: str = "http://localhost:9000"
    APP_VERSION: str = "0.1.0"

    DATABASE_URL: str = "postgresql+psycopg://triage:triage@localhost:5432/crm"
    DB_ECHO: bool = False

    LOGIN_MAX_FAILURES: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "demo"
    SEND_DEFAULT_PII: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_SHIPPER: str = "file"  # file | elasticsearch | null
    LOG_FILE_PATH: str = "logs/crm-ecs.jsonl"
    ELASTICSEARCH_URL: str | None = None
    ELASTICSEARCH_INDEX: str = "crm-logs"

    TAX_SERVICE_URL: str = "http://127.0.0.1:9010/api/tax-status"
    NOTES_SERVICE_URL: str = "http://127.0.0.1:9011/api/notes"
    TAX_TIMEOUT_SECONDS: float = 2.0

    # Stand switches — ignored unless CRM_MODE=experiment
    FAULT_IIN_SECOND_WEIGHTS: bool = False
    FAULT_NAME_SEARCH_RAW_SQL: bool = False
    FAULT_EXPORT_EMPTY_FIELD: bool = False
    FAULT_CORRUPT_RECORD: bool = False
    FAULT_TAX_TIMEOUT: bool = False
    FAULT_NOTES_DOWN: bool = False
    FAULT_POOL_EXHAUSTED: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_experiment(self) -> bool:
        mode = self.CRM_MODE if isinstance(self.CRM_MODE, str) else ""
        return mode.strip().lower() == "experiment"


def _resolve_sqlite(url: str, base: Path) -> str:
    if url.startswith("sqlite:///./"):
        rel = url.replace("sqlite:///./", "")
        return f"sqlite:///{(base / rel).resolve()}"
    return url


settings = Settings()
settings.DATABASE_URL = _resolve_sqlite(settings.DATABASE_URL, BASE_DIR)
