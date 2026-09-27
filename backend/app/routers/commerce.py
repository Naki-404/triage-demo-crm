from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ..auth import require_roles
from ..db import get_db
from ..models import Contract, Payment, User, UserRole
from ..schemas import (
    ContractCreate,
    ContractOut,
    CourseOut,
    EnrollIn,
    EnrollmentOut,
    InstallmentOut,
    InstallmentPlanIn,
    PackageOut,
    PaymentOut,
    PaymentWebhookIn,
)
from ..services import commerce
from ..services.commerce import CommerceError

router = APIRouter(tags=["commerce"])


def _http(exc: CommerceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/api/courses", response_model=list[CourseOut])
def courses(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer))):
    return [CourseOut.model_validate(c) for c in commerce.list_courses(db)]


@router.get("/api/packages", response_model=list[PackageOut])
def packages(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer))):
    out = []
    for p in commerce.list_packages(db):
        item = PackageOut.model_validate(p)
        item.course_ids = [i.course_id for i in p.items]
        out.append(item)
    return out


@router.post("/api/enrollments", response_model=list[EnrollmentOut], status_code=status.HTTP_201_CREATED)
def enroll(
    payload: EnrollIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    try:
        rows = commerce.enroll(
            db,
            user,
            client_id=payload.client_id,
            course_id=payload.course_id,
            package_id=payload.package_id,
            discount_pct=payload.discount_pct,
            price_override=payload.price_kzt,
        )
    except CommerceError as exc:
        raise _http(exc) from exc
    return [EnrollmentOut.model_validate(r) for r in rows]


@router.get("/api/clients/{client_id}/enrollments", response_model=list[EnrollmentOut])
def client_enrollments(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)),
):
    from ..models import Enrollment

    rows = db.query(Enrollment).filter(Enrollment.client_id == client_id).order_by(Enrollment.id.desc()).all()
    return [EnrollmentOut.model_validate(r) for r in rows]


@router.post("/api/contracts", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
def create_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    try:
        contract = commerce.create_contract(
            db,
            client_id=payload.client_id,
            number=payload.number,
            enrollment_ids=payload.enrollment_ids,
            discount_pct=payload.discount_pct,
            user=user,
        )
    except CommerceError as exc:
        raise _http(exc) from exc
    return ContractOut.model_validate(contract)


@router.get("/api/clients/{client_id}/contracts", response_model=list[ContractOut])
def client_contracts(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)),
):
    rows = db.query(Contract).filter(Contract.client_id == client_id).order_by(Contract.id.desc()).all()
    return [ContractOut.model_validate(r) for r in rows]


@router.post("/api/contracts/{contract_id}/installments", response_model=list[InstallmentOut])
def plan_installments(
    contract_id: int,
    payload: InstallmentPlanIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        rows = commerce.build_installment_schedule(db, contract, months=payload.months, first_due=payload.first_due)
    except CommerceError as exc:
        raise _http(exc) from exc
    return [InstallmentOut.model_validate(r) for r in rows]


@router.get("/api/contracts/{contract_id}/installments", response_model=list[InstallmentOut])
def list_installments(
    contract_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)),
):
    from ..models import Installment

    rows = db.query(Installment).filter(Installment.contract_id == contract_id).order_by(Installment.seq).all()
    return [InstallmentOut.model_validate(r) for r in rows]


@router.get("/api/contracts/{contract_id}/payments", response_model=list[PaymentOut])
def list_payments(
    contract_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)),
):
    rows = db.query(Payment).filter(Payment.contract_id == contract_id).order_by(Payment.id.desc()).all()
    return [PaymentOut.model_validate(r) for r in rows]


@router.post("/api/payments/webhook", response_model=PaymentOut)
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_signature: str = Header(default="", alias="X-Signature"),
    x_timestamp: str = Header(default="", alias="X-Timestamp"),
):
    body = await request.body()
    try:
        commerce.verify_payment_hmac(body, x_signature, x_timestamp)
        payload = PaymentWebhookIn.model_validate_json(body)
        payment = commerce.record_payment(
            db,
            contract_id=payload.contract_id,
            amount_kzt=payload.amount_kzt,
            external_id=payload.external_id,
            card_token=payload.card_token,
            card_last4=payload.card_last4,
        )
    except CommerceError as exc:
        raise _http(exc) from exc
    return PaymentOut.model_validate(payment)


@router.get("/api/contracts/{contract_id}/export/1c")
def export_1c(
    contract_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    try:
        data = commerce.export_1c_xml(db, contract_id)
    except CommerceError as exc:
        raise _http(exc) from exc
    return Response(content=data, media_type="application/xml", headers={"Content-Disposition": f'attachment; filename="contract-{contract_id}.xml"'})


@router.post("/api/integrations/1c/import")
async def import_1c(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    raw = await request.body()
    try:
        return commerce.import_1c_xml(db, raw)
    except CommerceError as exc:
        raise _http(exc) from exc
