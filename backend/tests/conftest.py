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

from decimal import Decimal

from app.auth import hash_password
from app.db import Base, get_db
from app.main import create_app
from app.models import Client, Course, Package, PackageItem, User, UserRole, utcnow
from app.iin import generate_iin
import random


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
        max_discount_pct=100,
    )
    manager = User(
        username="manager",
        email="manager@example.com",
        password_hash=hash_password("Manager-2026!"),
        role=UserRole.manager,
        is_active=True,
        max_discount_pct=15,
    )
    viewer = User(
        username="viewer",
        email="viewer@example.com",
        password_hash=hash_password("Viewer-2026!"),
        role=UserRole.viewer,
        is_active=True,
        max_discount_pct=0,
    )
    db_session.add_all([admin, manager, viewer])
    db_session.flush()

    c1 = Course(code="PY-101", title="Python", description="d", price_kzt=Decimal("120000"), created_at=utcnow())
    c2 = Course(code="DATA-110", title="SQL", description="d", price_kzt=Decimal("150000"), created_at=utcnow())
    db_session.add_all([c1, c2])
    db_session.flush()
    pkg = Package(code="PACK-START", title="Start", price_kzt=Decimal("280000"), created_at=utcnow())
    db_session.add(pkg)
    db_session.flush()
    db_session.add(PackageItem(package_id=pkg.id, course_id=c1.id))
    db_session.add(PackageItem(package_id=pkg.id, course_id=c2.id))

    rng = random.Random(1)
    for i, name in enumerate(["Айгуль Тестова", "Ерлан Тестов"]):
        db_session.add(
            Client(
                name=name,
                iin=generate_iin(rng),
                phone=f"+7701000000{i}",
                email=f"t{i}@example.kz",
                owner_id=manager.id,
            )
        )
    db_session.commit()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# Alias used by newer tests
@pytest.fixture()
def db(db_session):
    return db_session
