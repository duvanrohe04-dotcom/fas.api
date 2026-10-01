from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.models import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import Page, Pagination, build_page


class CategoryService:
    """Lógica de negocio de categorías."""

    def __init__(self, session: Session) -> None:
        """Guarda la sesión y el repositorio de categorías."""
        self.session = session
        self.categories = CategoryRepository(session)

    def get_or_404(self, category_id: int) -> Category:
        """Devuelve una categoría o lanza `NotFoundException`."""
        category = self.categories.get(category_id)
        if category is None:
            raise NotFoundException("Categoría no encontrada")
        return category

    def create(self, data: CategoryCreate) -> Category:
        """Crea una categoría. Falla si el nombre ya existe."""
        if self.categories.name_exists(data.name):
            raise BadRequestException("Ya existe una categoría con ese nombre")

        category = self.categories.create(name=data.name, description=data.description)
        self.session.commit()
        return category

    def list(self, pagination: Pagination) -> Page[CategoryRead]:
        """Devuelve una página de categorías."""
        result = self.categories.list(pagination)
        return build_page(
            [CategoryRead.model_validate(item) for item in result.items],
            result.total,
            pagination,
        )

    def update(self, category_id: int, data: CategoryUpdate) -> Category:
        """Actualiza parcialmente una categoría."""
        category = self.get_or_404(category_id)

        if data.name is not None and self.categories.name_exists(
            data.name, exclude_id=category_id
        ):
            raise BadRequestException("Ya existe una categoría con ese nombre")

        self.categories.update(
            category,
            name=data.name.strip() if data.name else None,
            description=data.description,
        )
        self.session.commit()
        return category

    def delete(self, category_id: int) -> None:
        """Elimina una categoría si no tiene productos activos asociados."""
        category = self.get_or_404(category_id)

        if self.categories.count_products(category_id) > 0:
            raise BadRequestException(
                "No se puede eliminar una categoría con productos activos"
            )

        self.categories.delete(category)
        self.session.commit()
