"""Create initial users and sample customers for local development."""
from __future__ import annotations

import argparse

from app.auth import hash_password
from app.db import Base, SessionLocal, engine
from app.iin import generate_iin
from app.models import Client, User, UserRole
import random


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


def seed(force: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        defaults = [
            ("admin", "admin@example.com", "Admin-2026!", UserRole.admin),
            ("manager", "manager@example.com", "Manager-2026!", UserRole.manager),
            ("viewer", "viewer@example.com", "Viewer-2026!", UserRole.viewer),
        ]
        for username, email, password, role in defaults:
            existing = db.query(User).filter(User.username == username).first()
            if existing and not force:
                continue
            if existing and force:
                existing.password_hash = hash_password(password)
                existing.role = role
                existing.email = email
                existing.is_active = True
                continue
            db.add(
                User(
                    username=username,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    is_active=True,
                )
            )
        db.commit()

        owner = db.query(User).filter(User.username == "manager").first() or db.query(User).first()
        if owner and db.query(Client).count() == 0:
            rng = random.Random(42)
            for name, phone, email in SAMPLE_CUSTOMERS:
                db.add(
                    Client(
                        name=name,
                        iin=generate_iin(rng),
                        phone=phone,
                        email=email,
                        owner_id=owner.id,
                    )
                )
            db.commit()
            print(f"seeded {len(SAMPLE_CUSTOMERS)} sample customers")
        else:
            print("customers already present — skip sample seed")

        print("seeded users: admin, manager, viewer")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    seed(force=args.force)
