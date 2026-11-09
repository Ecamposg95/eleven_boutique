"""Passwords, opaque sessions and the login lockout."""

import hashlib
import math
import secrets
from datetime import datetime, timedelta
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.api.errors import ApiError
from app.models import AdminSession, AdminUser, LoginAttempt
from app.models.base import utcnow
from app.services.admin import audit

COOKIE_NAME = "eleven_admin"
SESSION_TTL = timedelta(hours=12)
LOCK_WINDOW = timedelta(minutes=15)
MAX_FAILURES = 5
ATTEMPT_RETENTION = timedelta(days=1)
MIN_PASSWORD_LENGTH = 12

_hasher = PasswordHasher()  # Argon2id with the library's current recommended parameters.


def hash_password(password: str) -> str:
    return _hasher.hash(password)


@lru_cache
def _dummy_hash() -> str:
    return _hasher.hash(secrets.token_urlsafe(16))


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def _email_key(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _password_matches(stored_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _seconds_locked(db: Session, key: str, now: datetime) -> int:
    """0 when not locked. Keyed by email whether or not it exists, so it reveals nothing."""
    window_start = now - LOCK_WINDOW
    last_success = db.scalar(
        select(func.max(LoginAttempt.attempted_at)).where(
            LoginAttempt.email_key == key, LoginAttempt.succeeded.is_(True)
        )
    )
    failures = select(LoginAttempt.attempted_at).where(
        LoginAttempt.email_key == key,
        LoginAttempt.succeeded.is_(False),
        LoginAttempt.attempted_at > window_start,
    )
    if last_success is not None:
        failures = failures.where(LoginAttempt.attempted_at > last_success)
    recent = db.scalars(failures.order_by(LoginAttempt.attempted_at)).all()
    if len(recent) < MAX_FAILURES:
        return 0
    return max(1, math.ceil((recent[0] + LOCK_WINDOW - now).total_seconds()))


def login(db: Session, email: str, password: str) -> tuple[AdminUser, str]:
    """Returns the user and the raw token, which is never stored. Commits, so that failures count."""
    now = utcnow()
    normalized = normalize_email(email)
    key = _email_key(normalized)
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < now - ATTEMPT_RETENTION))

    locked_for = _seconds_locked(db, key, now)
    if locked_for:
        db.commit()
        raise ApiError(
            429,
            "too_many_attempts",
            "Demasiados intentos. Inténtalo más tarde.",
            headers={"Retry-After": str(locked_for)},
        )

    user = db.scalar(select(AdminUser).where(AdminUser.email == normalized))
    # An unknown email costs the same work as a wrong password.
    matches = _password_matches(user.password_hash if user else _dummy_hash(), password)
    if not (user and matches and user.is_active):
        db.add(LoginAttempt(email_key=key, succeeded=False, attempted_at=now))
        db.commit()
        raise ApiError(401, "invalid_credentials", "Correo o contraseña incorrectos")

    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = now
    db.add(LoginAttempt(email_key=key, succeeded=True, attempted_at=now))
    db.execute(delete(AdminSession).where(AdminSession.expires_at < now))
    token = secrets.token_urlsafe(32)
    db.add(AdminSession(user_id=user.id, token_hash=_token_hash(token), expires_at=now + SESSION_TTL))
    audit.record(db, user, "login", "admin_user", user.id)
    db.commit()
    return user, token


def find_session(db: Session, token: str | None) -> AdminSession | None:
    """The session behind a cookie, if it is live and its user still active."""
    if not token:
        return None
    session = db.scalar(
        select(AdminSession)
        .options(joinedload(AdminSession.user))
        .where(AdminSession.token_hash == _token_hash(token))
    )
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= utcnow()
        or not session.user.is_active
    ):
        return None
    return session


def logout(db: Session, session: AdminSession) -> None:
    session.revoked_at = utcnow()
    audit.record(db, session.user, "logout", "admin_user", session.user_id)
    db.commit()


def revoke_all_sessions(db: Session, user: AdminUser) -> None:
    now = utcnow()
    sessions = db.scalars(
        select(AdminSession).where(
            AdminSession.user_id == user.id, AdminSession.revoked_at.is_(None)
        )
    )
    for session in sessions:
        session.revoked_at = now
