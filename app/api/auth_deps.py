"""Authentication and authorization dependencies."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.api.deps import UnitOfWorkDep
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.models import User, UserRole
from app.services import AuthService

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/auth/login",
    auto_error=False,
    description="Token JWT de acceso emitido por /api/v1/auth/login.",
)


def get_auth_service(uow: UnitOfWorkDep) -> AuthService:
    """Provide an auth service bound to the request unit of work."""
    return AuthService(uow)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def _resolve_user(service: AuthService, token: str | None) -> User:
    """Validate a token and return the user it identifies."""
    if not token:
        raise AuthenticationError("Falta la cabecera Authorization: Bearer <token>")
    try:
        payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    except Exception as exc:
        raise AuthenticationError("Token inválido o expirado") from exc
    return service.get_active_user(int(payload["sub"]))


def get_current_user(
    service: AuthServiceDep,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    """Resolve the authenticated user from the bearer token."""
    return _resolve_user(service, token)


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_user(
    service: AuthServiceDep,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User | None:
    """Return the authenticated user when a valid token is present."""
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    except Exception:
        return None
    return service.get_active_user(int(payload["sub"]))


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Build a dependency that only allows the given roles."""
    allowed = set(roles)

    def dependency(current_user: CurrentUser) -> User:
        """Reject the request when the user role is not allowed."""
        if current_user.role not in allowed:
            logger.info(
                "Role not allowed",
                extra={"user_id": current_user.id, "role": current_user.role.value},
            )
            raise PermissionDeniedError(
                "No tienes permisos para realizar esta operación",
                details={"required_roles": sorted(role.value for role in allowed)},
            )
        return current_user

    return dependency


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
CashierUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER))]
StaffUser = Annotated[
    User,
    Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.WAITER)),
]

__all__ = [
    "AdminUser",
    "AuthServiceDep",
    "CashierUser",
    "CurrentUser",
    "OptionalUser",
    "StaffUser",
    "get_current_user",
    "get_optional_user",
    "require_roles",
]
