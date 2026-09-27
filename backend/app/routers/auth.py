from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from .. import vulns
from ..auth import (
    clear_login_failures,
    clear_session,
    create_session,
    get_current_user,
    is_locked,
    register_login_failure,
    require_roles,
    verify_password,
)
from ..db import get_db
from ..logging_ecs import request_id_var
from ..models import AuditLog, User, UserRole
from ..schemas import AuthOut, LoginIn, UserOut, UserPatch

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthOut)
def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    next: str | None = Query(default=None),
):
    user = db.query(User).filter(User.username == payload.username).first()
    # VULN_NO_RATE_LIMIT_LOGIN: skip lockout.
    if user and is_locked(user) and not vulns.no_rate_limit_login():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        if not vulns.no_rate_limit_login():
            register_login_failure(db, user)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    clear_login_failures(db, user)
    create_session(db, user, response)
    db.add(AuditLog(user_id=user.id, action="auth.login", request_id=request_id_var.get()))
    db.commit()
    out = AuthOut(user=UserOut.model_validate(user))
    # VULN_OPEN_REDIRECT intentional — reflect next without allowlist.
    if next:
        if vulns.open_redirect():
            response.headers["X-Redirect-To"] = next
        elif next.startswith("/") and not next.startswith("//"):
            response.headers["X-Redirect-To"] = next
    return out


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    clear_session(db, request, response)
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut)
def patch_me(
    payload: UserPatch,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)),
):
    data = payload.model_dump(exclude_unset=True)
    # VULN_MASS_ASSIGNMENT intentional — accept role from body.
    if "role" in data:
        if vulns.mass_assignment():
            user.role = data.pop("role")
        else:
            data.pop("role")
    if "email" in data and data["email"] is not None:
        user.email = str(data["email"])
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
