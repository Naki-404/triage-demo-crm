"""Create initial users, Bilim Academy catalogue and sample customers."""
from __future__ import annotations

import argparse
import random
from datetime import date
from decimal import Decimal

from app.auth import hash_password
from app.db import SessionLocal, ensure_schema
from app.iin import generate_iin
from app.models import (
    Client,
    Course,
    Package,
    PackageItem,
    User,
    UserRole,
    utcnow,
)

SAMPLE_CUSTOMERS = [
    ("Айгуль Нурланова", "+77011234567", "aigul.n@example.kz"),
    ("Ерлан Касымов", "+77022345678", "erlan.k@example.kz"),
    ("Дана Сейтова", "+77033456789", "dana.s@example.kz"),
    ("Нурлан Абдуллин", "+77044567890", "nurlan.a@example.kz"),
    ("Сауле Тулеуова", "+77055678901", "saule.t@example.kz"),
    ("Бахыт Жумабаев", "+77066789012", "bakhyt.zh@example.kz"),
    ("Асем Оспанова", "+77077890123", "assem.o@example.kz"),
    ("Тимур Ибраев", "+77088901234", "timur.i@example.kz"),
    ("Жанна Муратова", "+77099012345", "zhanna.m@example.kz"),
    ("Руслан Бекенов", "+77110123456", "ruslan.b@example.kz"),
]

COURSES = [
    ("PY-101", "Python для аналитиков", "Базовый Python", Decimal("120000")),
    ("WEB-201", "Веб-разработка", "HTML/CSS/JS + FastAPI", Decimal("180000")),
    ("SEC-301", "Основы кибербезопасности", "OWASP, логи, ИИН/ПДн", Decimal("220000")),
    ("DATA-110", "Данные и SQL", "PostgreSQL для бизнеса", Decimal("150000")),
]


def seed(force: bool = False) -> None:
    ensure_schema()
    db = SessionLocal()
    try:
        defaults = [
            ("admin", "admin@example.com", "Admin-2026!", UserRole.admin, 100),
            ("manager", "manager@example.com", "Manager-2026!", UserRole.manager, 15),
            ("viewer", "viewer@example.com", "Viewer-2026!", UserRole.viewer, 0),
        ]
        for username, email, password, role, max_disc in defaults:
            existing = db.query(User).filter(User.username == username).first()
            if existing and not force:
                existing.max_discount_pct = max_disc
                continue
            if existing and force:
                existing.password_hash = hash_password(password)
                existing.role = role
                existing.email = email
                existing.is_active = True
                existing.max_discount_pct = max_disc
                continue
            db.add(
                User(
                    username=username,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    is_active=True,
                    max_discount_pct=max_disc,
                )
            )
        db.commit()

        if db.query(Course).count() == 0:
            course_ids = {}
            for code, title, desc, price in COURSES:
                c = Course(code=code, title=title, description=desc, price_kzt=price, created_at=utcnow())
                db.add(c)
                db.flush()
                course_ids[code] = c.id
            pkg = Package(
                code="PACK-START",
                title="Стартовый пакет Bilim",
                price_kzt=Decimal("280000"),
                created_at=utcnow(),
            )
            db.add(pkg)
            db.flush()
            for code in ("PY-101", "DATA-110"):
                db.add(PackageItem(package_id=pkg.id, course_id=course_ids[code]))
            db.commit()
            print(f"seeded {len(COURSES)} courses + 1 package")
        else:
            print("catalogue already present — skip")

        owner = db.query(User).filter(User.username == "manager").first() or db.query(User).first()
        if owner and db.query(Client).count() == 0:
            rng = random.Random(42)
            for name, phone, email in SAMPLE_CUSTOMERS:
                iin = generate_iin(rng)
                # Derive a plausible birth date from IIN YYMMDD.
                yy, mm, dd = int(iin[0:2]), int(iin[2:4]), int(iin[4:6])
                year = 1900 + yy if yy > 50 else 2000 + yy
                try:
                    birth = date(year, mm, min(dd, 28))
                except ValueError:
                    birth = None
                db.add(
                    Client(
                        name=name,
                        iin=iin,
                        phone=phone,
                        email=email,
                        birth_date=birth,
                        owner_id=owner.id,
                    )
                )
            db.commit()
            print(f"seeded {len(SAMPLE_CUSTOMERS)} sample customers")
        else:
            print("customers already present — skip sample seed")

        print("seeded users: admin, manager, viewer (Bilim Academy)")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    seed(force=args.force)
