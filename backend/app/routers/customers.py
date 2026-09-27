from html import escape
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from .. import vulns
from ..auth import require_roles
from ..db import get_db
from ..iin import InvalidIINError
from ..models import Client, User, UserRole
from ..schemas import ClientCreate, ClientListOut, ClientOut, ClientUpdate
from ..services import customers
from ..services.customers import ExportError, PoolExhaustedError
from ..services.deps import DependencyError, check_tax_status

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    try:
        client = customers.create_client(
            db,
            user,
            name=payload.name,
            iin=payload.iin,
            phone=payload.phone,
            email=str(payload.email) if payload.email else None,
            birth_date=payload.birth_date,
        )
    except InvalidIINError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PoolExhaustedError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ClientOut.model_validate(client)


@router.get("", response_model=ClientListOut)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)),
):
    try:
        items, total = customers.list_clients(db, page=page, page_size=page_size, q=q)
    except PoolExhaustedError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ClientListOut(
        items=[ClientOut.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/search", response_model=list[ClientOut])
def search_customers(
    name: str | None = None,
    iin: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)),
):
    if name:
        try:
            found = customers.search_by_name(db, name)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
        except PoolExhaustedError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        return [ClientOut.model_validate(c) for c in found]
    if iin:
        client = customers.search_by_iin(db, iin)
        return [ClientOut.model_validate(client)] if client else []
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide name or iin")


@router.get("/export")
def export_customers(
    fmt: str = Query("csv", pattern="^(csv|xlsx)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    items, _ = customers.list_clients(db, page=1, page_size=10_000)
    try:
        if fmt == "xlsx":
            data = customers.export_xlsx(db, items)
            media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = "clients.xlsx"
        else:
            data = customers.export_csv(db, items)
            media = "text/csv"
            filename = "clients.csv"
    except ExportError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except TypeError as exc:
        # FAULT_EXPORT_NO_CONTRACT KeyError path surfaces as AttributeError/TypeError
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except AttributeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/file")
def download_export_file(
    name: str = Query(..., min_length=1),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    try:
        path = customers.safe_export_path(name)
    except ExportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    # Path traversal vuln may resolve outside EXPORT_DIR — intentional when flag on.
    return Response(content=path.read_bytes(), media_type="application/octet-stream")


@router.get("/{client_id}", response_model=ClientOut)
def get_customer(
    client_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)),
):
    try:
        client = customers.get_client(db, client_id, viewer=user)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="record error") from exc
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ClientOut.model_validate(client)


@router.patch("/{client_id}", response_model=ClientOut)
def update_customer(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"])
    for key, value in data.items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


@router.get("/{client_id}/tax")
def customer_tax(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        return check_tax_status(client.iin)
    except DependencyError as exc:
        detail = str(exc)
        code = status.HTTP_504_GATEWAY_TIMEOUT if "timed out" in detail else status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(status_code=code, detail=detail) from exc
