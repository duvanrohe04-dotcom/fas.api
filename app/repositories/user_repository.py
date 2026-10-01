from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import RoleEnum, User
from app.repositories.base import PaginatedResult, paginate
from app.schemas.common import Pagination


class UserRepository:
    """Acceso a datos de usuarios."""

    def __init__(self, session: Session) -> None:
        """Guarda la sesión de base de datos."""
        self.session = session

    def get(self, user_id: int) -> User | None:
        """Devuelve un usuario por su id, o `None` si no existe."""
        return self.session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        """Devuelve un usuario por su email, o `None` si no existe."""
        return self.session.execute(
            select(User).where(User.email == email.strip().lower())
        ).scalar_one_or_none()

    def email_exists(self, email: str) -> bool:
        """Indica si ya hay un usuario registrado con ese email."""
        return self.get_by_email(email) is not None

    def _base_query(
        self, *, role: RoleEnum | None = None, is_active: bool | None = None
    ) -> Select[User]:
        statement = select(User)
        if role is not None:
            statement = statement.where(User.role == role)
        if is_active is not None:
            statement = statement.where(User.is_active.is_(is_active))
        return statement

    def list(
        self,
        pagination: Pagination,
        *,
        role: RoleEnum | None = None,
        is_active: bool | None = None,
    ) -> PaginatedResult[User]:
        """Devuelve una página de usuarios filtrada opcionalmente por rol y estado."""
        statement = self._base_query(role=role, is_active=is_active).order_by(
            User.id.asc()
        )
        return paginate(self.session, statement, pagination)

    def create(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str,
        role: RoleEnum = RoleEnum.WAITER,
    ) -> User:
        """Persiste un nuevo usuario y lo devuelve."""
        user = User(
            email=email.strip().lower(),
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def delete(self, user: User) -> None:
        """Elimina un usuario de la base de datos."""
        self.session.delete(user)
        self.session.flush()
