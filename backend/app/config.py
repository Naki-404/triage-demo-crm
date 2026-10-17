from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    # clean | experiment | vuln — vuln enables VULN_* switches; experiment enables FAULT_*
    CRM_MODE: str = "clean"
    # The stand API (PATCH /api/stand) exists for the lab only; production refuses it unless explicitly enabled.
    STAND_CONTROL_ENABLED: bool = True
    SECRET_KEY: str = "change-me"
    COOKIE_SECURE: bool = False
    SESSION_EXPIRE_HOURS: int = 24
    CORS_ORIGINS: str = "http://localhost:5174,http://127.0.0.1:5174"
    BASE_URL: str = "http://localhost:9000"
    APP_VERSION: str = "0.2.0"
    COMPANY_NAME: str = "Bilim Academy"

    DATABASE_URL: str = "postgresql+psycopg://triage:triage@localhost:5432/crm"
    DB_ECHO: bool = False

    LOGIN_MAX_FAILURES: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    # Failed logins from one address (any account) before that address is locked for LOGIN_LOCKOUT_MINUTES
    LOGIN_IP_MAX_FAILURES: int = 20

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
    PAYMENT_WEBHOOK_SECRET: str = "bilim-demo-hmac-secret"
    PAYMENT_WEBHOOK_MAX_AGE_SECONDS: int = 300
    EXPORT_DIR: str = "exports"
    # Built frontend served by the API itself (Docker image); empty in development
    STATIC_DIR: str = ""

    # Stand switches — ignored unless CRM_MODE=experiment
    FAULT_IIN_SECOND_WEIGHTS: bool = False
    FAULT_NAME_SEARCH_RAW_SQL: bool = False
    FAULT_EXPORT_EMPTY_FIELD: bool = False
    FAULT_CORRUPT_RECORD: bool = False
    FAULT_TAX_TIMEOUT: bool = False
    FAULT_NOTES_DOWN: bool = False
    FAULT_POOL_EXHAUSTED: bool = False
    FAULT_PAYMENT_WEBHOOK: bool = False
    FAULT_DISCOUNT_STACK: bool = False
    FAULT_DUPLICATE_ENROLLMENT: bool = False
    FAULT_INSTALLMENT_ROUNDING: bool = False
    FAULT_EXPORT_NO_CONTRACT: bool = False

    # Vulnerability switches — ignored unless CRM_MODE=vuln
    VULN_SQLI_SEARCH: bool = False
    VULN_IDOR_CUSTOMER: bool = False
    VULN_MASS_ASSIGNMENT: bool = False
    VULN_STORED_XSS_NOTES: bool = False
    VULN_PATH_TRAVERSAL_EXPORT: bool = False
    VULN_SSRF_WEBHOOK: bool = False
    VULN_XXE_1C_IMPORT: bool = False
    VULN_NO_RATE_LIMIT_LOGIN: bool = False
    VULN_OPEN_REDIRECT: bool = False
    VULN_CSV_INJECTION: bool = False
    VULN_PRICE_TAMPERING: bool = False
    VULN_PAYMENT_SIGNATURE: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return (self.ENVIRONMENT or "").strip().lower() in ("production", "prod")

    @property
    def is_local(self) -> bool:
        """The app is only reachable from this machine (BASE_URL on loopback or a .localhost/.test name)."""
        from urllib.parse import urlparse

        host = (urlparse(self.BASE_URL).hostname or "").lower()
        return host in ("localhost", "127.0.0.1", "::1") or host.endswith((".localhost", ".test"))

    @property
    def is_experiment(self) -> bool:
        mode = (self.CRM_MODE or "").strip().lower()
        return mode == "experiment"

    @property
    def is_vuln(self) -> bool:
        mode = (self.CRM_MODE or "").strip().lower()
        return mode == "vuln"


def _resolve_sqlite(url: str, base: Path) -> str:
    if url.startswith("sqlite:///./"):
        rel = url.replace("sqlite:///./", "")
        return f"sqlite:///{(base / rel).resolve()}"
    return url


INSECURE_DEFAULTS = {"SECRET_KEY": "change-me", "PAYMENT_WEBHOOK_SECRET": "bilim-demo-hmac-secret"}


def production_problems(cfg: "Settings") -> list[str]:
    """Settings that must never reach production: default secrets and a non-clean stand mode.
    A lab stand reachable from outside (BASE_URL not on loopback) may run vuln/experiment modes, but never
    with the secrets committed to this repository."""
    if not cfg.is_production and cfg.is_local:
        return []
    problems = []
    for key, default in INSECURE_DEFAULTS.items():
        value = getattr(cfg, key, "") or ""
        if value == default or value.startswith("change-me") or len(value) < 16:
            problems.append(f"{key} has an insecure default")
    if not cfg.is_production:
        return problems
    if (cfg.CRM_MODE or "").lower() != "clean":
        problems.append("CRM_MODE must be clean in production")
    if cfg.STAND_CONTROL_ENABLED:
        problems.append("STAND_CONTROL_ENABLED must be false in production")
    return problems


settings = Settings()
settings.DATABASE_URL = _resolve_sqlite(settings.DATABASE_URL, BASE_DIR)
