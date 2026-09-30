"""Schemas for authentication and users."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.dates import as_utc
from app.models.user import UserRole

MIN_PASSWORD_LENGTH = 8
LOGIN_EXAMPLE = {"username": "admin", "password": "Admin1234"}


class LoginRequest(BaseModel):
    """Credentials used to obtain an access token."""

    model_config = ConfigDict(json_schema_extra={"example": LOGIN_EXAMPLE})

    username: str = Field(
        min_length=3,
        max_length=60,
        examples=["admin"],
        description="Nombre de usuario o correo electrónico.",
    )
    password: str = Field(
        min_length=1,
        max_length=72,
        examples=["Admin1234"],
        description="Contraseña del usuario.",
    )

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, value: str) -> str:
        """Trim the username and accept an email as identifier."""
        return value.strip().lower()


class RefreshRequest(BaseModel):
    """Payload to exchange a refresh token for a new access token."""

    model_config = ConfigDict(json_schema_extra={"example": {"refresh_token": "<jwt>"}})

    refresh_token: str = Field(description="Token de refresco emitido en el login.")


class UserRead(BaseModel):
    """Public representation of a staff member."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "username": "admin",
                "email": "admin@cafeteria.local",
                "full_name": "Administrador",
                "role": "admin",
                "is_active": True,
                "created_at": "2026-01-05T10:00:00Z",
            }
        },
    )

    id: int = Field(examples=[1])
    username: str = Field(examples=["admin"])
    email: str = Field(examples=["admin@cafeteria.local"])
    full_name: str = Field(examples=["Administrador"])
    role: UserRole = Field(examples=["admin"])
    is_active: bool = Field(examples=[True])
    created_at: datetime

    @classmethod
    def from_model(cls, user: Any) -> UserRead:
        """Build the response payload from an ORM user."""
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=as_utc(user.created_at),
        )


class TokenResponse(BaseModel):
    """Tokens issued after a successful login."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "<jwt>",
                "refresh_token": "<jwt>",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }
    )

    access_token: str = Field(description="JWT de acceso para las cabeceras Authorization.")
    refresh_token: str = Field(description="JWT de refresco.")
    token_type: str = Field(default="bearer", examples=["bearer"])
    expires_in: int = Field(description="Segundos de validez del token de acceso.")


class PasswordChange(BaseModel):
    """Payload to change the password of the authenticated user."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"current_password": "Admin1234", "new_password": "Nuevo12345"}
        }
    )

    current_password: str = Field(max_length=72, description="Contraseña actual.")
    new_password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        max_length=72,
        description="Nueva contraseña, mínimo 8 caracteres.",
    )
