from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, Token, UserCreate, UserRead


class AuthService:
    """Lógica de negocio de autenticación y registro."""

    def __init__(self, session: Session) -> None:
        """Guarda la sesión y el repositorio de usuarios."""
        self.session = session
        self.users = UserRepository(session)

    def register(self, data: UserCreate) -> User:
        """Registra un usuario nuevo. Falla si el email ya está en uso."""
        if self.users.email_exists(data.email):
            raise BadRequestException("El email ya está registrado")

        user = self.users.create(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )
        self.session.commit()
        return user

    def authenticate(self, credentials: LoginRequest) -> tuple[User, str]:
        """Comprueba las credenciales y devuelve el usuario junto a su token."""
        user = self.users.get_by_email(credentials.email)
        if user is None or not verify_password(
            credentials.password, user.hashed_password
        ):
            raise UnauthorizedException("Email o contraseña incorrectos")
        if not user.is_active:
            raise UnauthorizedException("El usuario está inactivo")

        token = create_access_token(user.id, role=user.role.value)
        return user, token

    def login(self, credentials: LoginRequest) -> Token:
        """Inicia sesión y devuelve el token junto con los datos del usuario."""
        user, token = self.authenticate(credentials)
        return Token(
            access_token=token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserRead.model_validate(user),
        )

    def get_active_user(self, user_id: int) -> User:
        """Devuelve el usuario asociado al token, verificando que siga activo."""
        user = self.users.get(user_id)
        if user is None:
            raise UnauthorizedException("Usuario no encontrado")
        if not user.is_active:
            raise UnauthorizedException("El usuario está inactivo")
        return user


def create_user_if_empty(session: Session, data: UserCreate) -> User | None:
    """Crea el usuario indicado solo si no hay ningún usuario en la base de datos."""
    existing = session.execute(select(func.count()).select_from(User)).scalar_one()
    if existing:
        return None
    return AuthService(session).register(data)
