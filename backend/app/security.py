"""Auth primitives — bcrypt hashing + JWT (Section 0.1).

Passwords hashed with bcrypt via passlib. JWTs signed with settings.JWT_SECRET.
Access + refresh tokens per 0.4; expiry from 0.5 env config.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def _create_token(sub: str, expires: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(
        str(user_id),
        timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MIN),
        "access",
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        str(user_id),
        timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
        "refresh",
    )


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """Decode + validate a JWT. Raises JWTError on any problem."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    if expected_type is not None and payload.get("type") != expected_type:
        raise JWTError(f"expected {expected_type} token, got {payload.get('type')}")
    return payload
