import hashlib
from datetime import datetime

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
    request.state.user_id = user.id
    return user


# A hash that is verified when the user name does not exist, so a missing account costs the same time as a wrong
# password and the login endpoint does not leak which user names are real.
_DUMMY_HASH = hash_password("dummy-password-for-timing")

# Failed logins per client address; one address trying many accounts is locked like one account trying many passwords.
_ip_failures: dict[str, tuple[int, datetime]] = {}


def verify_or_burn(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        verify_password(password, _DUMMY_HASH)
        return False
    return verify_password(password, password_hash)


def ip_locked(ip: str | None) -> bool:
    if not ip:
        return False
    count, until = _ip_failures.get(ip, (0, utcnow()))
    return count >= settings.LOGIN_IP_MAX_FAILURES and until > utcnow()


def register_ip_failure(ip: str | None) -> None:
    if not ip:
        return
    from datetime import timedelta

    count, until = _ip_failures.get(ip, (0, utcnow()))
    if until <= utcnow():
        count = 0
    _ip_failures[ip] = (count + 1, utcnow() + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES))
    if len(_ip_failures) > 10_000:
        # drop expired entries first, then the oldest ones; never wipe active locks wholesale
        now = utcnow()
        for key in [k for k, (_, t) in _ip_failures.items() if t <= now]:
            _ip_failures.pop(key, None)
        while len(_ip_failures) > 10_000:
            _ip_failures.pop(next(iter(_ip_failures)))


def clear_ip_failures(ip: str | None) -> None:
    if ip:
        _ip_failures.pop(ip, None)


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
