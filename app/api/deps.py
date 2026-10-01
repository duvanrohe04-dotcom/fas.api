from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.models import RoleEnum, User
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_auth_service(session: DbSession) -> AuthService:
    """Devuelve el servicio de autenticación ligado a la sesión de la petición."""
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Resuelve el usuario autenticado a partir del token Bearer."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedException("Falta la cabecera Authorization")

    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedException("Token inválido")

    try:
        user_id = int(subject)
    except ValueError as exc:
        raise UnauthorizedException("Token inválido") from exc

    return AuthService(session).get_active_user(user_id)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: RoleEnum) -> Callable[[User], User]:
    """Crea una dependencia que exige que el usuario tenga uno de los roles dados."""

    def _dependency(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise ForbiddenException("No tienes permisos para esta operación")
        return current_user

    return _dependency


AdminUser = Annotated[User, Depends(require_roles(RoleEnum.ADMIN))]
StaffUser = Annotated[User, Depends(require_roles(RoleEnum.ADMIN, RoleEnum.CASHIER))]
WaiterUser = Annotated[User, Depends(require_roles(RoleEnum.WAITER))]
