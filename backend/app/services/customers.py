"""Customer card service: create, list, search, export. Stand switches select alternate code paths."""
from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable

from openpyxl import Workbook
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import faults
from ..iin import validate_iin
from ..models import Client, User


class ExportError(RuntimeError):
    pass


def create_client(db: Session, owner: User, *, name: str, iin: str, phone: str | None, email: str | None) -> Client:
    validate_iin(iin)
    if db.query(Client).filter(Client.iin == iin).first():
        raise ValueError("Client with this IIN already exists")
    client = Client(name=name, iin=iin, phone=phone, email=email, owner_id=owner.id)
    if faults.corrupt_record_enabled():
        client.meta_json = "{"
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def list_clients(db: Session, *, page: int, page_size: int, q: str | None = None) -> tuple[list[Client], int]:
    query = db.query(Client)
    if q:
        like = f"%{q}%"
        query = query.filter((Client.name.ilike(like)) | (Client.iin.like(like)))
    total = query.count()
    items = query.order_by(Client.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def search_by_name(db: Session, name: str) -> list[Client]:
    if faults.name_search_uses_raw_sql():
        # Alternate implementation used by the experiment stand (parameter concatenation).
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
    return db.query(Client).filter(Client.iin == iin).first()


def get_client(db: Session, client_id: int) -> Client | None:
    client = db.get(Client, client_id)
    if client is None:
        return None
    if client.meta_json:
        json.loads(client.meta_json)
    return client


def _row(client: Client) -> dict[str, str]:
    phone = client.phone or ""
    email = client.email or ""
    if faults.export_fails_on_empty_field() and (phone == "" or email == ""):
        raise ExportError(f"cannot export client {client.id}: required field is empty")
    return {
        "id": str(client.id),
        "name": client.name,
        "iin": client.iin,
        "phone": phone,
        "email": email,
    }


def export_csv(clients: Iterable[Client]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["id", "name", "iin", "phone", "email"])
    writer.writeheader()
    for client in clients:
        writer.writerow(_row(client))
    return buf.getvalue().encode("utf-8")


def export_xlsx(clients: Iterable[Client]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "clients"
    ws.append(["id", "name", "iin", "phone", "email"])
    for client in clients:
        row = _row(client)
        ws.append([row["id"], row["name"], row["iin"], row["phone"], row["email"]])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
