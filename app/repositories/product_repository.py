from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Product
from app.repositories.base import PaginatedResult, paginate
from app.schemas.common import Pagination


class ProductRepository:
    """Acceso a datos de productos."""

    def __init__(self, session: Session) -> None:
        """Guarda la sesión de base de datos."""
        self.session = session

    def get(self, product_id: int) -> Product | None:
        """Devuelve un producto por su id, o `None` si no existe."""
        return self.session.execute(
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == product_id)
        ).scalar_one_or_none()

    def get_by_name(self, name: str) -> Product | None:
        """Devuelve un producto por su nombre, o `None` si no existe."""
        return self.session.execute(
            select(Product).where(func.lower(Product.name) == name.strip().lower())
        ).scalar_one_or_none()

    def name_exists(self, name: str, *, exclude_id: int | None = None) -> bool:
        """Indica si el nombre ya está en uso por otro producto."""
        existing = self.get_by_name(name)
        return existing is not None and existing.id != exclude_id

    def category_exists(self, category_id: int) -> bool:
        """Indica si la categoría indicada existe."""
        return (
            self.session.execute(
                select(func.count())
                .select_from(Category)
                .where(Category.id == category_id)
            ).scalar_one()
            > 0
        )

    def _base_query(
        self,
        *,
        category_id: int | None = None,
        is_active: bool | None = None,
    ) -> Select[Product]:
        statement = select(Product).options(selectinload(Product.category))
        if category_id is not None:
            statement = statement.where(Product.category_id == category_id)
        if is_active is not None:
            statement = statement.where(Product.is_active.is_(is_active))
        return statement

    def list(
        self,
        pagination: Pagination,
        *,
        category_id: int | None = None,
        is_active: bool | None = None,
    ) -> PaginatedResult[Product]:
        """Devuelve una página de productos filtrada por categoría y estado."""
        statement = self._base_query(
            category_id=category_id, is_active=is_active
        ).order_by(Product.name.asc())
        return paginate(self.session, statement, pagination)

    def create(
        self,
        *,
        name: str,
        description: str | None,
        price: float,
        stock: int,
        category_id: int,
    ) -> Product:
        """Persiste un nuevo producto y lo devuelve."""
        product = Product(
            name=name.strip(),
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
        )
        self.session.add(product)
        self.session.flush()
        return product

    def update(self, product: Product, **changes: object) -> Product:
        """Aplica cambios parciales a un producto."""
        for field, value in changes.items():
            if value is not None:
                setattr(product, field, value)
        self.session.flush()
        return product

    def delete(self, product: Product) -> None:
        """Elimina un producto de la base de datos."""
        self.session.delete(product)
        self.session.flush()
