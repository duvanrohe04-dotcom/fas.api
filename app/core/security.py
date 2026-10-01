from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

ALGORITHM = "HS256"

# bcrypt solo considera los primeros 72 bytes de la contraseña.
BCRYPT_MAX_BYTES = 72


def _prepare_password(password: str) -> bytes:
    """Codifica la contraseña y la recorta al límite de bcrypt."""
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(_prepare_password(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Comprueba una contraseña en texto plano contra su hash bcrypt."""
    try:
        return bcrypt.checkpw(
            _prepare_password(password), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: int | str,
    *,
    role: str | None = None,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Crea un JWT de acceso firmado con `SECRET_KEY`."""
    now = datetime.now(UTC)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    claims: dict[str, Any] = {"sub": str(subject), "iat": now, "exp": expire}
    if role is not None:
        claims["role"] = role
    if extra_claims:
        claims.update(extra_claims)

    return jwt.encode(claims, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un JWT. Lanza `UnauthorizedException` si no es válido."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedException("El token ha expirado") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedException("Token inválido") from exc
