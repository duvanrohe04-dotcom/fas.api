"""Authentication service: credentials, tokens and password changes."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, BusinessRuleError
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User, UserRole
from app.repositories import UnitOfWork
from app.schemas.auth import TokenResponse

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 8


class AuthService:
    """Handle login, token refresh and password management."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Store the unit of work used for data access and transactions."""
        self.uow = uow
        self.repository = uow.users

    def authenticate(self, identifier: str, password: str) -> User:
        """Validate the credentials and return the authenticated user."""
        user = self.repository.get_by_identifier(identifier)
        if user is None or not verify_password(password, user.hashed_password):
            logger.info("Failed login attempt", extra={"identifier": identifier})
            raise AuthenticationError("Usuario o contraseña incorrectos")
        if not user.is_active:
            raise AuthenticationError("El usuario está desactivado")
        logger.info("User logged in", extra={"user_id": user.id, "role": user.role.value})
        return user

    def issue_tokens(self, user: User) -> TokenResponse:
        """Create an access/refresh token pair for the given user."""
        settings = get_settings()
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def login(self, identifier: str, password: str) -> tuple[User, TokenResponse]:
        """Authenticate the user and return them together with their tokens."""
        user = self.authenticate(identifier, password)
        return user, self.issue_tokens(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        """Issue a new access token from a valid refresh token."""
        try:
            payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        except Exception as exc:
            raise AuthenticationError("Token de refresco inválido o expirado") from exc
        user = self.get_active_user(int(payload["sub"]))
        return self.issue_tokens(user)

    def get_active_user(self, user_id: int) -> User:
        """Return an active user or raise an authentication error."""
        user = self.repository.get(user_id)
        if user is None:
            raise AuthenticationError("El usuario del token no existe")
        if not user.is_active:
            raise AuthenticationError("El usuario está desactivado")
        return user

    def change_password(self, user: User, *, current_password: str, new_password: str) -> None:
        """Replace the password of the authenticated user."""
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("La contraseña actual no es correcta")
        if current_password == new_password:
            raise BusinessRuleError("La nueva contraseña debe ser distinta de la actual")
        self._assert_password_strength(new_password)
        user.hashed_password = hash_password(new_password)
        self.uow.commit()
        logger.info("Password changed", extra={"user_id": user.id})

    def create_user(
        self,
        *,
        username: str,
        email: str,
        full_name: str,
        password: str,
        role: UserRole = UserRole.WAITER,
    ) -> User:
        """Create a new staff member (admin only operation)."""
        self._assert_password_strength(password)
        if self.repository.get_by_identifier(username):
            raise BusinessRuleError(f"El usuario '{username}' ya existe")
        user = self.repository.create(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
        )
        self.uow.commit()
        logger.info("User created", extra={"user_id": user.id, "role": role.value})
        return user

    @staticmethod
    def _assert_password_strength(password: str) -> None:
        """Reject passwords that are too short or too simple."""
        if len(password) < MIN_PASSWORD_LENGTH:
            raise BusinessRuleError(
                f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres"
            )
        if password.isdigit() or password.isalpha():
            raise BusinessRuleError("La contraseña debe combinar letras y números")


def user_id_from_token(token: str) -> int:
    """Extract the user id from a validated access token."""
    payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    return int(payload["sub"])
