import hashlib

from fastapi import Depends, HTTPException, Request, Response, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import SessionToken, User, UserRole, new_session_token, session_expiry, utcnow

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
COOKIE = "crm_session"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User, response: Response) -> SessionToken:
    raw = new_session_token()
    row = SessionToken(user_id=user.id, token_hash=hash_token(raw), expires_at=session_expiry(settings.SESSION_EXPIRE_HOURS))
    db.add(row)
    db.commit()
    response.set_cookie(
        COOKIE,
        raw,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_EXPIRE_HOURS * 3600,
    )
    return row


def clear_session(db: Session, request: Request, response: Response) -> None:
    raw = request.cookies.get(COOKIE)
    if raw:
        db.query(SessionToken).filter(SessionToken.token_hash == hash_token(raw)).delete()
        db.commit()
    response.delete_cookie(COOKIE)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    row = db.query(SessionToken).filter(SessionToken.token_hash == hash_token(raw)).first()
    if row is None or row.expires_at < utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_roles(*roles: UserRole):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dep


def register_login_failure(db: Session, user: User | None) -> None:
    if user is None:
        return
    user.failed_logins = (user.failed_logins or 0) + 1
    if user.failed_logins >= settings.LOGIN_MAX_FAILURES:
        from datetime import timedelta

        user.locked_until = utcnow() + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
        user.failed_logins = 0
    db.commit()


def clear_login_failures(db: Session, user: User) -> None:
    user.failed_logins = 0
    user.locked_until = None
    db.commit()


def is_locked(user: User) -> bool:
    return bool(user.locked_until and user.locked_until > utcnow())
