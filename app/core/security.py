"""Password hashing and JSON Web Token helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Final

import bcrypt
import jwt

from app.core.config import get_settings

ACCESS_TOKEN_TYPE: Final[str] = "access"
REFRESH_TOKEN_TYPE: Final[str] = "refresh"
BCRYPT_MAX_BYTES: Final[int] = 72

settings = get_settings()


def _encode(password: str) -> bytes:
    """Encode a password, enforcing the bcrypt 72 byte limit."""
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Return a bcrypt hash for the given plain password."""
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plain password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(_encode(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    """Build a signed JWT for the given subject."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """Create a short lived access token."""
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    return _create_token(str(subject), ACCESS_TOKEN_TYPE, timedelta(minutes=minutes))


def create_refresh_token(subject: str | int, expires_days: int | None = None) -> str:
    """Create a long lived refresh token."""
    days = expires_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
    return _create_token(str(subject), REFRESH_TOKEN_TYPE, timedelta(days=days))


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """Decode and validate a JWT, raising ValueError when invalid."""
    payload: dict[str, Any] = jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=[settings.ALGORITHM],
    )
    if expected_type is not None and payload.get("type") != expected_type:
        raise ValueError(f"Expected token type '{expected_type}'")
    if not payload.get("sub"):
        raise ValueError("Token has no subject")
    return payload
