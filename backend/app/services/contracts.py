"""Contracts and 1C integration."""
from __future__ import annotations

from decimal import Decimal
from xml.etree import ElementTree as ET

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException
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
    if not enrollment_ids or len(set(enrollment_ids)) != len(enrollment_ids):
        raise CommerceError("A contract needs distinct enrollments", 400)
    enrollments = db.query(Enrollment).filter(Enrollment.id.in_(enrollment_ids), Enrollment.client_id == client_id).all()
    if len(enrollments) != len(enrollment_ids):
        raise CommerceError("Enrollment mismatch", 400)
    if any(e.contract_id is not None for e in enrollments):
        raise CommerceError("Enrollment is already on a contract", 409)
    total = sum((e.price_kzt for e in enrollments), Decimal("0"))
    already_discounted = any(e.discount_pct for e in enrollments)
    if discount_pct and already_discounted and not faults.discount_stacks():
        # One discount per sale: either on the enrollment or on the contract, never both.
        raise CommerceError("Enrollments already carry a discount; the contract cannot add another", 409)
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
        # Decode first (a UTF-16 document hides "<!DOCTYPE" from a byte search), then let defusedxml refuse
        # DTDs, entities and external references regardless of how they are spelled.
        text = _decode_xml(raw)
        if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise CommerceError("XML with DOCTYPE/ENTITY is not allowed", 400)
        try:
            root = SafeET.fromstring(text, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        except DefusedXmlException as exc:
            raise CommerceError("XML with DOCTYPE/ENTITY is not allowed", 400) from exc
        except ET.ParseError as exc:
            raise CommerceError("Malformed XML", 400) from exc
    number = root.findtext("Number") or root.findtext(".//{urn:1c:bilim}Number")
    return {"number": number, "ok": True}


def _decode_xml(raw: bytes) -> str:
    for bom, encoding in ((b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"), (b"\xef\xbb\xbf", "utf-8-sig")):
        if raw.startswith(bom):
            return raw.decode(encoding, errors="replace")
    if len(raw) > 1 and raw[0] == 0x3C and raw[1] == 0:
        return raw.decode("utf-16-le", errors="replace")
    if len(raw) > 1 and raw[0] == 0 and raw[1] == 0x3C:
        return raw.decode("utf-16-be", errors="replace")
    return raw.decode("utf-8", errors="replace")
