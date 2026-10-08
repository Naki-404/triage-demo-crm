from sqlalchemy import create_engine, event
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
    """Bring DB to Alembic head (stamp empty DBs, upgrade otherwise)."""
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext

    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
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
