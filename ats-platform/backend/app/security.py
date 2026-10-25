"""Password hashing and JWT helpers.

Secrets stay server-side. Tokens are short-lived JWTs; the frontend stores them
and sends them as a bearer token.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from .config import settings


def hash_password(password: str) -> str:
    # bcrypt only considers the first 72 bytes; truncate defensively.
    return bcrypt.hashpw(password[:72].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain[:72].encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject: str, extra: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


def create_signed_token(resource: str, ttl_seconds: int) -> str:
    """Short-lived signed token used for private file downloads."""
    expire = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    return jwt.encode(
        {"sub": resource, "scope": "file", "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def verify_signed_token(token: str) -> str | None:
    data = decode_token(token)
    if not data or data.get("scope") != "file":
        return None
    return data.get("sub")
