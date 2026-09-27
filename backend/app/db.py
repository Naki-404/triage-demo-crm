from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_fk(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def ensure_schema() -> None:
    """Create missing tables/columns and align Alembic revision.

    Local DBs often grew via create_all before migrations existed; plain
    ``alembic upgrade`` would fail recreating tables. This brings SQLite/Postgres
    up to the current models, then stamps or upgrades Alembic to head.
    """
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext

    # Import models so metadata is complete.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        insp = inspect(conn)
        if insp.has_table("users"):
            cols = {c["name"] for c in insp.get_columns("users")}
            if "max_discount_pct" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN max_discount_pct INTEGER NOT NULL DEFAULT 10"))
        if insp.has_table("clients"):
            cols = {c["name"] for c in insp.get_columns("clients")}
            if "birth_date" not in cols:
                conn.execute(text("ALTER TABLE clients ADD COLUMN birth_date DATE"))

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    with engine.connect() as conn:
        current = MigrationContext.configure(conn).get_current_revision()
    if current is None:
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
