"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.auth_deps import AuthServiceDep, CurrentUser
from app.schemas.auth import (
    LoginRequest,
    PasswordChange,
    RefreshRequest,
    TokenResponse,
    UserRead,
)
from app.schemas.common import ErrorResponse, Message

router = APIRouter(prefix="/auth", tags=["Auth"])

AUTH_ERROR = {401: {"model": ErrorResponse, "description": "Credenciales o token inválidos"}}


@router.post(
    "/login",
    summary="Iniciar sesión",
    description=(
        "Autentica al usuario y devuelve un par de tokens JWT. Acepta `username` o "
        "`email` como identificador. El token de acceso se envía en la cabecera "
        "`Authorization: Bearer <access_token>`."
    ),
    response_model=TokenResponse,
    responses={
        200: {"description": "Sesión iniciada"},
        **AUTH_ERROR,
    },
)
def login(payload: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    """Authenticate a user with JSON credentials."""
    _, tokens = service.login(payload.username, payload.password)
    return tokens


@router.post(
    "/login/form",
    summary="Iniciar sesión (formulario OAuth2)",
    description="Flujo OAuth2 `password` usado por el botón de autorización de /docs.",
    response_model=TokenResponse,
    responses={200: {"description": "Sesión iniciada"}, **AUTH_ERROR},
)
def login_form(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
) -> TokenResponse:
    """Authenticate a user using the OAuth2 password form."""
    identifier = form_data.username
    _, tokens = service.login(identifier, form_data.password)
    return tokens


@router.post(
    "/refresh",
    summary="Renovar token",
    description="Emite un nuevo token de acceso a partir de un token de refresco válido.",
    response_model=TokenResponse,
    responses={200: {"description": "Token renovado"}, **AUTH_ERROR},
)
def refresh_tokens(payload: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    """Issue a new access token from a refresh token."""
    return service.refresh(payload.refresh_token)


@router.get(
    "/me",
    summary="Perfil actual",
    description="Devuelve los datos del usuario autenticado.",
    response_model=UserRead,
    responses={200: {"description": "Perfil del usuario"}, **AUTH_ERROR},
)
def read_profile(current_user: CurrentUser) -> UserRead:
    """Return the authenticated user profile."""
    return UserRead.from_model(current_user)


@router.post(
    "/change-password",
    summary="Cambiar contraseña",
    description="Permite al usuario autenticado cambiar su propia contraseña.",
    response_model=Message,
    responses={
        200: {"description": "Contraseña actualizada"},
        401: {"model": ErrorResponse, "description": "La contraseña actual no coincide"},
        422: {"model": ErrorResponse, "description": "La nueva contraseña es débil"},
    },
)
def change_password(
    payload: PasswordChange,
    current_user: CurrentUser,
    service: AuthServiceDep,
) -> Message:
    """Change the password of the authenticated user."""
    service.change_password(
        current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return Message(detail="Contraseña actualizada correctamente")


@router.post(
    "/logout",
    summary="Cerrar sesión",
    description=(
        "Los tokens son sin estado, por lo que el cliente simplemente debe descartar el "
        "`refresh_token`."
    ),
    response_model=Message,
    responses={200: {"description": "Sesión cerrada"}},
)
def logout(_: CurrentUser) -> Message:
    """Acknowledge the client side token disposal."""
    return Message(detail="Sesión cerrada correctamente")
