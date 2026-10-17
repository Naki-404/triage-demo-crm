"""Demo database for the stand UI: a year of a small training centre's sales.

    python -m app.seed --demo          (after the base seed; idempotent)

Deterministic (fixed seed) and internally consistent: IINs pass the checksum, installment schedules sum to the
contract total, past installments are paid by a matching payment or marked overdue, completed contracts are fully
paid. The base seed (tests, the trainer's dataset builder) is not affected: this only runs with --demo.
"""
from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from .iin import generate_iin
from .models import (
    Client,
    ClientNote,
    Contract,
    ContractStatus,
    Course,
    Enrollment,
    Installment,
    InstallmentStatus,
    Package,
    PackageItem,
    Payment,
    PaymentStatus,
    User,
    UserRole,
)

DEMO_SEED = 2026
DEMO_CLIENTS = 320
DEMO_MARKER = json.dumps({"demo": True})
TWO = Decimal("0.01")

EXTRA_MANAGERS = [("aliya", "aliya@bilim.example.kz", 15), ("daniyar", "daniyar@bilim.example.kz", 20)]

EXTRA_COURSES = [
    ("PY-201", "Python: автоматизация и API", "requests, FastAPI, планировщики", Decimal("160000")),
    ("BI-120", "Power BI и визуализация", "дашборды для бизнеса", Decimal("140000")),
    ("ML-310", "Машинное обучение на практике", "sklearn, валидация, деплой", Decimal("260000")),
    ("PM-150", "Управление IT-проектами", "Scrum, Kanban, риски", Decimal("130000")),
    ("QA-130", "Тестирование ПО", "ручное и автоматизированное", Decimal("125000")),
    ("ENG-IT", "Английский для IT", "B1–B2, собеседования", Decimal("90000")),
]
EXTRA_PACKAGES = [
    ("PACK-DATA", "Аналитик данных: полный путь", Decimal("390000"), ("DATA-110", "BI-120", "PY-101")),
    ("PACK-DEV", "Backend-разработчик", Decimal("320000"), ("PY-101", "PY-201")),
]

MALE_FIRST = ["Ерлан", "Нурлан", "Тимур", "Руслан", "Бахыт", "Арман", "Данияр", "Асхат", "Мади", "Ержан", "Олжас", "Санжар",
              "Айдос", "Бекзат", "Нуржан", "Алмас", "Ильяс", "Марат", "Дмитрий", "Сергей", "Алексей", "Артём", "Максим", "Азамат"]
FEMALE_FIRST = ["Айгуль", "Дана", "Сауле", "Асем", "Жанна", "Мадина", "Алия", "Камила", "Динара", "Айжан", "Гульнара", "Томирис",
                "Аружан", "Жансая", "Карина", "Анна", "Екатерина", "Мария", "Ольга", "Индира", "Асель", "Меруерт", "Зарина", "Лаура"]
SURNAMES = ["Нурланов", "Касымов", "Сейтов", "Абдуллин", "Тулеуов", "Жумабаев", "Оспанов", "Ибраев", "Муратов", "Бекенов",
            "Сарсенбаев", "Ахметов", "Омаров", "Кенжебаев", "Садыков", "Мухамедов", "Есенов", "Байжанов", "Искаков", "Токтаров",
            "Иванов", "Ким", "Петров", "Смагулов", "Утепов", "Жаксылыков", "Рахимов", "Аубакиров", "Нуриев", "Серикбаев"]
TRANSLIT = str.maketrans({"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y",
                          "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
                          "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"})
MAIL_DOMAINS = ["gmail.com", "mail.ru", "inbox.kz", "yandex.kz", "outlook.com"]
NOTE_TEMPLATES = [
    "Позвонил, интересуется вечерним форматом.",
    "Отправили программу курса на почту.",
    "Просит рассрочку на 6 месяцев.",
    "Оплата задерживается, обещал до конца недели.",
    "Прошёл вводное занятие, всё понравилось.",
    "Нужна справка для работодателя.",
    "Хочет перевестись в другую группу.",
    "Спрашивал про скидку для студентов.",
    "Уточнить удобное время для звонка.",
    "Договорились о встрече в офисе.",
]


def _money(value: Decimal) -> Decimal:
    return value.quantize(TWO, rounding=ROUND_HALF_UP)


def _name(rng: random.Random) -> str:
    if rng.random() < 0.5:
        return f"{rng.choice(MALE_FIRST)} {rng.choice(SURNAMES)}"
    surname = rng.choice(SURNAMES)
    surname = surname if surname in ("Ким",) else surname + "а"
    return f"{rng.choice(FEMALE_FIRST)} {surname}"


def _email(name: str, n: int, rng: random.Random) -> str:
    first, last = name.lower().translate(TRANSLIT).split()[:2]
    return f"{first}.{last}{n % 97}@{rng.choice(MAIL_DOMAINS)}"


def _phone(rng: random.Random) -> str:
    return f"+7{rng.choice(['701', '702', '705', '707', '708', '747', '771', '775', '777', '778'])}{rng.randint(1000000, 9999999)}"


def _birth_date(iin: str) -> date | None:
    yy, mm, dd = int(iin[0:2]), int(iin[2:4]), int(iin[4:6])
    century = {"1": 1800, "2": 1800, "3": 1900, "4": 1900, "5": 2000, "6": 2000}.get(iin[6], 1900)
    try:
        return date(century + yy, mm, dd)
    except ValueError:
        return None


def _ensure_staff(db: Session, password_for) -> list[User]:
    from .auth import hash_password

    for username, email, max_disc in EXTRA_MANAGERS:
        if not db.query(User).filter(User.username == username).first():
            db.add(User(username=username, email=email, password_hash=hash_password(password_for(username)),
                        role=UserRole.manager, is_active=True, max_discount_pct=max_disc))
    db.commit()
    return db.query(User).filter(User.role == UserRole.manager).order_by(User.id).all()


def _ensure_catalogue(db: Session) -> tuple[list[Course], list[Package]]:
    for code, title, desc, price in EXTRA_COURSES:
        if not db.query(Course).filter(Course.code == code).first():
            db.add(Course(code=code, title=title, description=desc, price_kzt=price))
    db.commit()
    by_code = {c.code: c for c in db.query(Course).all()}
    for code, title, price, items in EXTRA_PACKAGES:
        if not db.query(Package).filter(Package.code == code).first():
            pkg = Package(code=code, title=title, price_kzt=price)
            db.add(pkg)
            db.flush()
            for course_code in items:
                if course_code in by_code:
                    db.add(PackageItem(package_id=pkg.id, course_id=by_code[course_code].id))
    db.commit()
    return db.query(Course).filter(Course.is_active.is_(True)).order_by(Course.id).all(), db.query(Package).all()


def populate(db: Session, password_for, today: date | None = None) -> dict[str, int]:
    """Add the demo year once; returns what was created (all zeros when it is already there)."""
    counts = {"managers": 0, "clients": 0, "enrollments": 0, "contracts": 0, "installments": 0, "payments": 0, "notes": 0}
    if db.query(Client).filter(Client.meta_json == DEMO_MARKER).first():
        return counts
    rng = random.Random(DEMO_SEED)
    today = today or date.today()
    now = datetime.combine(today, datetime.now().time()) if today == date.today() else datetime.combine(today, datetime.max.time())
    managers = _ensure_staff(db, password_for)
    counts["managers"] = len(managers)
    courses, _packages = _ensure_catalogue(db)
    used_iins = {iin for (iin,) in db.query(Client.iin).all()}
    contract_seq = db.query(Contract).count()

    for n in range(DEMO_CLIENTS):
        while True:
            iin = generate_iin(rng)
            if iin not in used_iins and _birth_date(iin) and 1960 <= _birth_date(iin).year <= 2006:
                used_iins.add(iin)
                break
        name = _name(rng)
        created = datetime.combine(today - timedelta(days=rng.randint(0, 365)), datetime.min.time()) + timedelta(hours=rng.randint(9, 19), minutes=rng.randint(0, 59))
        created = min(created, now - timedelta(hours=1))
        client = Client(
            name=name, iin=iin, phone=_phone(rng) if rng.random() > 0.04 else None,
            email=_email(name, n, rng) if rng.random() > 0.08 else None, birth_date=_birth_date(iin),
            owner_id=rng.choice(managers).id, meta_json=DEMO_MARKER, created_at=created, updated_at=created,
        )
        db.add(client)
        db.flush()
        counts["clients"] += 1

        for _ in range(rng.choices([0, 1, 2, 3], weights=[2, 5, 3, 1])[0]):
            note_at = min(created + timedelta(days=rng.randint(0, max((today - created.date()).days, 0)), hours=rng.randint(0, 6)), now)
            db.add(ClientNote(client_id=client.id, author_id=client.owner_id, body=rng.choice(NOTE_TEMPLATES), created_at=note_at))
            counts["notes"] += 1

        if rng.random() > 0.72:
            continue  # a lead: no enrollment yet
        chosen = rng.sample(courses, k=rng.choices([1, 2], weights=[4, 1])[0])
        enrollment_discount = rng.choices([0, 5, 10], weights=[7, 2, 1])[0]
        enrolled_at = created + timedelta(days=rng.randint(0, 14))
        enrollments = []
        for course in chosen:
            price = _money(Decimal(course.price_kzt) * (100 - enrollment_discount) / 100)
            e = Enrollment(client_id=client.id, course_id=course.id, price_kzt=price, discount_pct=enrollment_discount, created_at=enrolled_at)
            db.add(e)
            enrollments.append(e)
            counts["enrollments"] += 1
        db.flush()
        if rng.random() > 0.8:
            continue  # enrolled, contract not drawn up yet

        status = rng.choices([ContractStatus.active, ContractStatus.completed, ContractStatus.draft, ContractStatus.cancelled], weights=[55, 25, 12, 8])[0]
        months = rng.choices([1, 3, 6, 12], weights=[3, 3, 3, 1])[0]
        contract_discount = 0 if enrollment_discount else rng.choices([0, 5, 10, 15], weights=[6, 2, 2, 1])[0]
        total = _money(sum((e.price_kzt for e in enrollments), Decimal("0")) * (100 - contract_discount) / 100)
        contract_seq += 1
        signed = enrolled_at + timedelta(days=rng.randint(1, 10))
        if status == ContractStatus.completed and signed.date() + timedelta(days=30 * (months - 1)) > today:
            status = ContractStatus.active  # a schedule that is not over yet cannot be completed
        contract = Contract(
            number=f"BA-{signed.year}-{contract_seq:04d}", client_id=client.id, status=status, total_kzt=total,
            discount_pct=contract_discount, created_at=enrolled_at, signed_at=None if status == ContractStatus.draft else signed,
        )
        db.add(contract)
        db.flush()
        for e in enrollments:
            e.contract_id = contract.id
        counts["contracts"] += 1
        if status == ContractStatus.draft:
            continue

        each = _money(total / months)
        amounts = [each] * (months - 1) + [_money(total - each * (months - 1))]
        late_payer = status == ContractStatus.active and rng.random() < 0.18
        for seq, amount in enumerate(amounts, start=1):
            due = signed.date() + timedelta(days=30 * (seq - 1))
            inst_status = InstallmentStatus.scheduled
            if status == ContractStatus.cancelled:
                inst_status = InstallmentStatus.paid if seq == 1 else InstallmentStatus.cancelled
            elif status == ContractStatus.completed or due <= today:
                inst_status = InstallmentStatus.overdue if (late_payer and due <= today and due > today - timedelta(days=75)) else InstallmentStatus.paid
            if months > 1:
                db.add(Installment(contract_id=contract.id, seq=seq, due_date=due, amount_kzt=amount, status=inst_status))
                counts["installments"] += 1
            if inst_status == InstallmentStatus.paid:
                paid_at = datetime.combine(due + timedelta(days=rng.randint(-3, 4)), datetime.min.time()) + timedelta(hours=rng.randint(9, 21), minutes=rng.randint(0, 59))
                paid_at = min(paid_at, now - timedelta(minutes=rng.randint(5, 600)))  # never in the future
                if rng.random() < 0.03:
                    db.add(Payment(contract_id=contract.id, amount_kzt=amount, status=PaymentStatus.failed, card_last4=f"{rng.randint(0, 9999):04d}",
                                   external_id=f"demo-{contract.id}-{seq}-fail", created_at=paid_at, paid_at=None))
                    counts["payments"] += 1
                db.add(Payment(contract_id=contract.id, amount_kzt=amount, status=PaymentStatus.paid, card_last4=f"{rng.randint(0, 9999):04d}",
                               external_id=f"demo-{contract.id}-{seq}", created_at=paid_at, paid_at=paid_at))
                counts["payments"] += 1
        db.flush()
    db.commit()
    return counts


def reset(db: Session) -> int:
    """Remove the demo year (clients marked as demo and everything that hangs off them); returns clients removed."""
    ids = [cid for (cid,) in db.query(Client.id).filter(Client.meta_json == DEMO_MARKER).all()]
    if not ids:
        return 0
    contract_ids = [cid for (cid,) in db.query(Contract.id).filter(Contract.client_id.in_(ids)).all()]
    db.query(Payment).filter(Payment.contract_id.in_(contract_ids)).delete(synchronize_session=False)
    db.query(Installment).filter(Installment.contract_id.in_(contract_ids)).delete(synchronize_session=False)
    db.query(Enrollment).filter(Enrollment.client_id.in_(ids)).delete(synchronize_session=False)
    db.query(Contract).filter(Contract.id.in_(contract_ids)).delete(synchronize_session=False)
    db.query(ClientNote).filter(ClientNote.client_id.in_(ids)).delete(synchronize_session=False)
    db.query(Client).filter(Client.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return len(ids)
