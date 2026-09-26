import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force sqlite before app imports resolve settings
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["CRM_MODE"] = "clean"
os.environ["LOG_SHIPPER"] = "null"
os.environ["SECRET_KEY"] = "test-secret"

from app.auth import hash_password
from app.db import Base, get_db
from app.main import create_app
from app.models import User, UserRole


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    app = create_app()

    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override

    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("Admin-2026!"),
        role=UserRole.admin,
        is_active=True,
    )
    manager = User(
        username="manager",
        email="manager@example.com",
        password_hash=hash_password("Manager-2026!"),
        role=UserRole.manager,
        is_active=True,
    )
    viewer = User(
        username="viewer",
        email="viewer@example.com",
        password_hash=hash_password("Viewer-2026!"),
        role=UserRole.viewer,
        is_active=True,
    )
    db_session.add_all([admin, manager, viewer])
    db_session.commit()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
