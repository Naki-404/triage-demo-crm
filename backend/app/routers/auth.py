from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from .. import vulns
from ..auth import (
    clear_ip_failures,
    clear_login_failures,
    clear_session,
    create_session,
    get_current_user,
    ip_locked,
    is_locked,
    register_ip_failure,
    register_login_failure,
    require_roles,
    verify_or_burn,
)
from ..db import get_db
from ..logging_ecs import request_id_var
from ..models import AuditLog, User, UserRole
from ..observe import emit
from ..schemas import AuthOut, LoginIn, UserOut, UserPatch, WebhookTestOut
from ..services import webhooks

# one test ping per user per WEBHOOK_TEST_INTERVAL_S: the endpoint makes an outbound request
WEBHOOK_TEST_INTERVAL_S = 10
_last_webhook_test: dict[int, float] = {}

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthOut)
def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    next: str | None = Query(default=None),
):
    ip = request.client.host if request.client else None
    user = db.query(User).filter(User.username == payload.username).first()
    rate_limited = not vulns.no_rate_limit_login()
    if rate_limited and ((user and is_locked(user)) or ip_locked(ip)):
        emit("auth.login_locked", "warning", "login refused: account or address locked", request, username=payload.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_or_burn(payload.password, user.password_hash if user else None) or user is None or not user.is_active:
        if rate_limited:
            register_login_failure(db, user)
            register_ip_failure(ip)
        emit("auth.login_failed", "warning", "invalid credentials", request, username=payload.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    clear_login_failures(db, user)
    clear_ip_failures(ip)
    request.state.user_id = user.id
    create_session(db, user, response)
    db.add(AuditLog(user_id=user.id, action="auth.login", request_id=request_id_var.get()))
    db.commit()
    out = AuthOut(user=UserOut.model_validate(user))
    if next:
        if vulns.open_redirect():  # noqa: SIM114 — keep vuln vs safe branches explicit for stand demos
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
    if "role" in data:
        if vulns.mass_assignment():
            user.role = data.pop("role")
        else:
            data.pop("role")
    if "email" in data and data["email"] is not None:
        user.email = str(data["email"])
    if "webhook_url" in data:
        url = data["webhook_url"]
        if url and not vulns.ssrf_webhook():
            url = webhooks.validate_webhook_url(url)
        user.webhook_url = url or None
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/me/webhook/test", response_model=WebhookTestOut)
def test_webhook(
    request: Request,
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    """Ping the profile webhook once."""
    if not user.webhook_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No webhook configured")
    import time

    now = time.monotonic()
    if now - _last_webhook_test.get(user.id, 0.0) < WEBHOOK_TEST_INTERVAL_S:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Try again in a few seconds")
    _last_webhook_test[user.id] = now
    result = webhooks.send_test(user.webhook_url)
    emit("profile.webhook_test", "info", f"webhook test -> {result['status_code']}", request)
    return WebhookTestOut(**result)
