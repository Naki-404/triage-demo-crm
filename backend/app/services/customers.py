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
from ..iin import validate_iin
from ..models import Client, Contract, User


class ExportError(RuntimeError):
    pass


class PoolExhaustedError(RuntimeError):
    pass


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


def list_clients(db: Session, *, page: int, page_size: int, q: str | None = None) -> tuple[list[Client], int]:
    _check_pool()
    query = db.query(Client)
    if q:
        like = f"%{q}%"
        query = query.filter((Client.name.ilike(like)) | (Client.iin.like(like)))
    total = query.count()
    items = query.order_by(Client.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def search_by_name(db: Session, name: str) -> list[Client]:
    _check_pool()
    # VULN_SQLI_SEARCH intentional, experiment only — raw concatenation.
    if vulns.sqli_search() or faults.name_search_uses_raw_sql():
        sql = text(f"SELECT id FROM clients WHERE name = '{name}'")
        try:
            ids = [row[0] for row in db.execute(sql).all()]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc
        if not ids:
            return []
        return db.query(Client).filter(Client.id.in_(ids)).all()
    return db.query(Client).filter(Client.name == name).all()


def search_by_iin(db: Session, iin: str) -> Client | None:
    _check_pool()
    return db.query(Client).filter(Client.iin == iin).first()


def get_client(db: Session, client_id: int, viewer: User | None = None) -> Client | None:
    _check_pool()
    client = db.get(Client, client_id)
    if client is None:
        return None
    # Clean path: managers only see own clients unless admin. VULN_IDOR skips check.
    if viewer is not None and not vulns.idor_customer():
        if viewer.role.value != "admin" and client.owner_id != viewer.id and viewer.role.value != "viewer":
            # managers: own only; viewers: all (read); admin: all
            if viewer.role.value == "manager" and client.owner_id != viewer.id:
                return None
    if client.meta_json:
        json.loads(client.meta_json)
    return client


def _contract_number(db: Session, client: Client) -> str:
    contract = (
        db.query(Contract)
        .filter(Contract.client_id == client.id)
        .order_by(Contract.id.desc())
        .first()
    )
    if faults.export_requires_no_contract_bug():
        # Bug: assume contract always exists → KeyError when missing.
        return contract.number  # type: ignore[union-attr]
    return contract.number if contract else ""


def _row(db: Session, client: Client) -> dict[str, str]:
    phone = client.phone or ""
    email = client.email or ""
    if faults.export_fails_on_empty_field() and (phone == "" or email == ""):
        raise ExportError(f"cannot export client {client.id}: required field is empty")
    contract_no = _contract_number(db, client)
    name = client.name
    # VULN_CSV_INJECTION intentional — do not sanitize formula prefixes.
    if not vulns.csv_injection():
        if name and name[0] in ("=", "+", "-", "@"):
            name = "'" + name
    return {
        "id": str(client.id),
        "name": name,
        "iin": client.iin,
        "phone": phone,
        "email": email,
        "contract": contract_no,
    }


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


def safe_export_path(filename: str) -> Path:
    base = Path(settings.EXPORT_DIR).resolve()
    base.mkdir(parents=True, exist_ok=True)
    # VULN_PATH_TRAVERSAL_EXPORT intentional — join without sanitizing.
    if vulns.path_traversal_export():
        return (base / filename).resolve()
    candidate = (base / Path(filename).name).resolve()
    if not str(candidate).startswith(str(base)):
        raise ExportError("invalid export path")
    return candidate
