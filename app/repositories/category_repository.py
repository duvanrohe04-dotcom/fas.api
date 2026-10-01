from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Category, Product
from app.repositories.base import PaginatedResult, paginate
from app.schemas.common import Pagination


class CategoryRepository:
    """Acceso a datos de categorías."""

    def __init__(self, session: Session) -> None:
        """Guarda la sesión de base de datos."""
        self.session = session

    def get(self, category_id: int) -> Category | None:
        """Devuelve una categoría por su id, o `None` si no existe."""
        return self.session.execute(
            select(Category).where(Category.id == category_id)
        ).scalar_one_or_none()

    def get_by_name(self, name: str) -> Category | None:
        """Devuelve una categoría por su nombre, o `None` si no existe."""
        return self.session.execute(
            select(Category).where(func.lower(Category.name) == name.strip().lower())
        ).scalar_one_or_none()

    def name_exists(self, name: str, *, exclude_id: int | None = None) -> bool:
        """Indica si el nombre ya está en uso por otra categoría."""
        existing = self.get_by_name(name)
        return existing is not None and existing.id != exclude_id

    def _base_query(self) -> Select[Category]:
        return select(Category)

    def list(self, pagination: Pagination) -> PaginatedResult[Category]:
        """Devuelve una página de categorías ordenadas por nombre."""
        statement = self._base_query().order_by(Category.name.asc())
        return paginate(self.session, statement, pagination)

    def create(self, *, name: str, description: str | None) -> Category:
        """Persiste una nueva categoría y la devuelve."""
        category = Category(name=name.strip(), description=description)
        self.session.add(category)
        self.session.flush()
        return category

    def update(self, category: Category, **changes: object) -> Category:
        """Aplica cambios parciales a una categoría."""
        for field, value in changes.items():
            if value is not None:
                setattr(category, field, value)
        self.session.flush()
        return category

    def delete(self, category: Category) -> None:
        """Elimina una categoría de la base de datos."""
        self.session.delete(category)
        self.session.flush()

    def count_products(self, category_id: int) -> int:
        """Cuenta los productos activos asociados a una categoría."""
        return self.session.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.category_id == category_id, Product.is_active.is_(True))
        ).scalar_one()
