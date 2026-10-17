"""Customer card service: create, list, search, export. Stand switches select alternate code paths."""
from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import faults, vulns
from ..config import settings
from ..errors import DomainError
from ..iin import validate_iin
from ..models import Client, Contract, User, UserRole
from .access import ClientAccessError, assert_can_access


class ExportError(DomainError):
    status_code = 500


class PoolExhaustedError(DomainError):
    status_code = 503


class RecordError(DomainError):
    """A stored record cannot be read back (corrupt serialisation): the client gets a generic 500."""

    status_code = 500


FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value: str) -> str:
    """Spreadsheet-safe cell: a leading formula character is quoted so Excel/LibreOffice do not evaluate it."""
    if value and value[0] in FORMULA_PREFIXES:
        return "'" + value
    return value


def _check_pool() -> None:
    if faults.pool_exhausted():
        raise PoolExhaustedError("database connection pool exhausted")


def create_client(
    db: Session,
    owner: User,
    *,
    name: str,
    iin: str,
    phone: str | None,
    email: str | None,
    birth_date=None,
) -> Client:
    _check_pool()
    validate_iin(iin)
    if db.query(Client).filter(Client.iin == iin).first():
        raise ValueError("Client with this IIN already exists")
    client = Client(name=name, iin=iin, phone=phone, email=email, birth_date=birth_date, owner_id=owner.id)
    if faults.corrupt_record_enabled():
        client.meta_json = "{"
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _scoped(query, viewer: User | None):
    """Managers see their own clients; admins and viewers see everything (the IDOR flag lifts the scope)."""
    if viewer is not None and viewer.role == UserRole.manager and not vulns.idor_customer():
        return query.filter(Client.owner_id == viewer.id)
    return query


def list_clients(db: Session, *, page: int, page_size: int, q: str | None = None, viewer: User | None = None) -> tuple[list[Client], int]:
    _check_pool()
    query = _scoped(db.query(Client), viewer)
    if q:
        like = f"%{q}%"
        query = query.filter((Client.name.ilike(like)) | (Client.iin.like(like)))
    total = query.count()
    items = query.order_by(Client.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def search_by_name(db: Session, name: str, viewer: User | None = None) -> list[Client]:
    _check_pool()
    if vulns.sqli_search() or faults.name_search_uses_raw_sql():
        sql = text(f"SELECT id FROM clients WHERE name = '{name}'")
        try:
            ids = [row[0] for row in db.execute(sql).all()]
        except Exception as exc:
            # The database error (and the injected SQL) is for the log; the client sees a generic 500.
            db.rollback()
            raise RecordError("search failed") from exc
        if not ids:
            return []
        return _scoped(db.query(Client).filter(Client.id.in_(ids)), viewer).all()
    return _scoped(db.query(Client).filter(Client.name == name), viewer).all()


def search_by_iin(db: Session, iin: str, viewer: User | None = None) -> Client | None:
    _check_pool()
    return _scoped(db.query(Client).filter(Client.iin == iin), viewer).first()


def get_client(db: Session, client_id: int, viewer: User | None = None) -> Client | None:
    _check_pool()
    client = db.get(Client, client_id)
    if client is None:
        return None
    if viewer is not None:
        try:
            assert_can_access(viewer, client)
        except ClientAccessError:
            return None
    if client.meta_json:
        try:
            json.loads(client.meta_json)
        except ValueError as exc:
            raise RecordError("record error") from exc
    return client


def update_client(db: Session, client_id: int, user: User, data: dict) -> Client | None:
    _check_pool()
    client = db.get(Client, client_id)
    if client is None:
        return None
    assert_can_access(user, client)
    if user.role not in (UserRole.admin, UserRole.manager):
        raise PermissionError("Forbidden")
    for key, value in data.items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return client


def client_for_user(db: Session, client_id: int, user: User) -> Client | None:
    """Load client or None when missing or access denied."""
    _check_pool()
    client = db.get(Client, client_id)
    if client is None:
        return None
    try:
        assert_can_access(user, client)
    except ClientAccessError:
        return None
    return client


def _contract_number(db: Session, client: Client) -> str:
    contract = (
        db.query(Contract)
        .filter(Contract.client_id == client.id)
        .order_by(Contract.id.desc())
        .first()
    )
    if faults.export_requires_no_contract_bug():
        return contract.number  # type: ignore[union-attr]
    return contract.number if contract else ""


def _row(db: Session, client: Client) -> dict[str, str]:
    phone = client.phone or ""
    email = client.email or ""
    if faults.export_fails_on_empty_field() and (phone == "" or email == ""):
        raise ExportError(f"cannot export client {client.id}: required field is empty")
    contract_no = _contract_number(db, client)
    row = {
        "id": str(client.id),
        "name": client.name,
        "iin": client.iin,
        "phone": phone,
        "email": email,
        "contract": contract_no,
    }
    if vulns.csv_injection():
        return row
    return {key: csv_safe(value) for key, value in row.items()}


def export_csv(db: Session, clients: Iterable[Client]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["id", "name", "iin", "phone", "email", "contract"])
    writer.writeheader()
    for client in clients:
        writer.writerow(_row(db, client))
    return buf.getvalue().encode("utf-8")


def export_xlsx(db: Session, clients: Iterable[Client]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "clients"
    ws.append(["id", "name", "iin", "phone", "email", "contract"])
    for client in clients:
        row = _row(db, client)
        ws.append([row["id"], row["name"], row["iin"], row["phone"], row["email"], row["contract"]])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def safe_export_path(filename: str, user_id: int | None = None) -> Path:
    base = Path(settings.EXPORT_DIR).resolve()
    base.mkdir(parents=True, exist_ok=True)
    if vulns.path_traversal_export():
        return (base / filename).resolve()
    if user_id is not None:
        # one folder per user: a manager can never download the file an admin exported (all clients)
        base = (base / f"u{int(user_id)}").resolve()
    candidate = (base / Path(filename).name).resolve()
    if not str(candidate).startswith(str(base)):
        raise ExportError("invalid export path")
    return candidate
