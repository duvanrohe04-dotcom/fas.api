from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.schemas.auth import LoginRequest, Token, UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(session: DbSession) -> AuthService:
    """Devuelve el servicio de autenticación ligado a la sesión de la petición."""
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/login", response_model=Token, summary="Iniciar sesión")
def login(payload: LoginRequest, service: AuthServiceDep) -> Token:
    """
    Autentica al usuario y devuelve un token JWT junto con sus datos.
    """
    return service.login(payload)


@router.get("/me", response_model=UserRead, summary="Usuario autenticado")
def read_current_user(current_user: CurrentUser) -> UserRead:
    """
    Devuelve los datos del usuario asociado al token enviado.
    """
    return UserRead.model_validate(current_user)


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario (solo admin)",
)
def create_user(payload: UserCreate, service: AuthServiceDep, _: AdminUser) -> UserRead:
    """
    Crea un usuario con el rol que se indique. Requiere token de administrador.
    """
    return UserRead.model_validate(service.register(payload))
