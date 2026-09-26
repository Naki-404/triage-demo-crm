from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ..auth import (
    clear_login_failures,
    clear_session,
    create_session,
    get_current_user,
    is_locked,
    register_login_failure,
    verify_password,
)
from ..db import get_db
from ..logging_ecs import request_id_var
from ..models import AuditLog, User
from ..schemas import AuthOut, LoginIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user and is_locked(user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        register_login_failure(db, user)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    clear_login_failures(db, user)
    create_session(db, user, response)
    db.add(AuditLog(user_id=user.id, action="auth.login", request_id=request_id_var.get()))
    db.commit()
    return AuthOut(user=UserOut.model_validate(user))


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    clear_session(db, request, response)
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)
