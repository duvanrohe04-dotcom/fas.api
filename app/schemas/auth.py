from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import RoleEnum


class UserRead(BaseModel):
    """Representación pública de un usuario (nunca incluye el hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: RoleEnum
    is_active: bool


class UserCreate(BaseModel):
    """Datos necesarios para registrar un usuario."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: RoleEnum = RoleEnum.WAITER


class LoginRequest(BaseModel):
    """Credenciales para iniciar sesión."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Token(BaseModel):
    """Respuesta de autenticación."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Segundos de validez del token.")
    user: UserRead
