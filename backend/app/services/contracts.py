"""Contracts and 1C integration."""
from __future__ import annotations

from decimal import Decimal
from xml.etree import ElementTree as ET

from sqlalchemy.orm import Session

from .. import faults, vulns
from ..models import Client, Contract, ContractStatus, Enrollment, User, utcnow
from .access import assert_can_access
from .commerce_pricing import CommerceError, apply_discount, check_discount_allowed


def list_for_client(db: Session, client_id: int) -> list[Contract]:
    return db.query(Contract).filter(Contract.client_id == client_id).order_by(Contract.id.desc()).all()


def create_contract(
    db: Session,
    *,
    client_id: int,
    number: str,
    enrollment_ids: list[int],
    discount_pct: int = 0,
    user: User,
) -> Contract:
    client = db.get(Client, client_id)
    if client is None:
        raise CommerceError("Client not found", 404)
    assert_can_access(user, client)

    check_discount_allowed(user, discount_pct)
    if db.query(Contract).filter(Contract.number == number).first():
        raise CommerceError("Contract number already exists", 409)
    enrollments = db.query(Enrollment).filter(Enrollment.id.in_(enrollment_ids), Enrollment.client_id == client_id).all()
    if len(enrollments) != len(enrollment_ids):
        raise CommerceError("Enrollment mismatch", 400)
    total = sum((e.price_kzt for e in enrollments), Decimal("0"))
    if discount_pct and not faults.discount_stacks():
        total = apply_discount(total, discount_pct)
    elif discount_pct and faults.discount_stacks():
        total = apply_discount(apply_discount(total, discount_pct), discount_pct)
    contract = Contract(
        number=number,
        client_id=client_id,
        status=ContractStatus.active,
        total_kzt=total.quantize(Decimal("0.01")),
        discount_pct=discount_pct,
        signed_at=utcnow(),
    )
    db.add(contract)
    db.flush()
    for e in enrollments:
        e.contract_id = contract.id
    db.commit()
    db.refresh(contract)
    return contract


def export_1c_xml(db: Session, contract_id: int) -> bytes:
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise CommerceError("Contract not found", 404)
    root = ET.Element("Document", {"xmlns": "urn:1c:bilim"})
    ET.SubElement(root, "Number").text = contract.number
    ET.SubElement(root, "ClientId").text = str(contract.client_id)
    ET.SubElement(root, "Total").text = str(contract.total_kzt)
    ET.SubElement(root, "Status").text = contract.status.value
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def import_1c_xml(db: Session, raw: bytes) -> dict:
    if vulns.xxe_1c_import():
        parser = ET.XMLParser()
        text = raw.decode("utf-8", errors="replace")
        if "SYSTEM" in text and "file://" in text.lower():
            raise CommerceError("XXE payload accepted (vuln demo)", 500)
        root = ET.fromstring(raw, parser=parser)
    else:
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise CommerceError("XML with DOCTYPE/ENTITY is not allowed", 400)
        root = ET.fromstring(raw)
    number = root.findtext("Number") or root.findtext(".//{urn:1c:bilim}Number")
    return {"number": number, "ok": True}
