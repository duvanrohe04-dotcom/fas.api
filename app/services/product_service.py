from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.models import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.common import Page, Pagination, build_page
from app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductStockUpdate,
    ProductUpdate,
)


class ProductService:
    """Lógica de negocio de productos."""

    def __init__(self, session: Session) -> None:
        """Guarda la sesión y el repositorio de productos."""
        self.session = session
        self.products = ProductRepository(session)

    def get_or_404(self, product_id: int) -> Product:
        """Devuelve un producto o lanza `NotFoundException`."""
        product = self.products.get(product_id)
        if product is None:
            raise NotFoundException("Producto no encontrado")
        return product

    def create(self, data: ProductCreate) -> Product:
        """Crea un producto. Falla si el nombre existe o la categoría no."""
        if self.products.name_exists(data.name):
            raise BadRequestException("Ya existe un producto con ese nombre")
        if not self.products.category_exists(data.category_id):
            raise BadRequestException("La categoría indicada no existe")

        product = self.products.create(
            name=data.name,
            description=data.description,
            price=data.price,
            stock=data.stock,
            category_id=data.category_id,
        )
        self.session.commit()
        return product

    def list(
        self,
        pagination: Pagination,
        *,
        category_id: int | None = None,
        is_active: bool | None = None,
    ) -> Page[ProductRead]:
        """Devuelve una página de productos filtrada."""
        result = self.products.list(
            pagination, category_id=category_id, is_active=is_active
        )
        return build_page(
            [ProductRead.model_validate(item) for item in result.items],
            result.total,
            pagination,
        )

    def update(self, product_id: int, data: ProductUpdate) -> Product:
        """Actualiza parcialmente un producto."""
        product = self.get_or_404(product_id)

        if data.name is not None and self.products.name_exists(
            data.name, exclude_id=product_id
        ):
            raise BadRequestException("Ya existe un producto con ese nombre")
        if data.category_id is not None and not self.products.category_exists(
            data.category_id
        ):
            raise BadRequestException("La categoría indicada no existe")

        self.products.update(
            product,
            name=data.name.strip() if data.name else None,
            description=data.description,
            price=data.price,
            stock=data.stock,
            category_id=data.category_id,
            is_active=data.is_active,
        )
        self.session.commit()
        return product

    def adjust_stock(self, product_id: int, data: ProductStockUpdate) -> Product:
        """Ajusta el stock de forma absoluta o mediante un delta."""
        if data.stock is None and data.delta is None:
            raise BadRequestException("Indica `stock` o `delta`")

        product = self.get_or_404(product_id)

        if data.stock is not None:
            new_stock = data.stock
        else:
            new_stock = product.stock + (data.delta or 0)

        if new_stock < 0:
            raise BadRequestException("El stock no puede ser negativo")

        product.stock = new_stock
        self.session.flush()
        self.session.commit()
        return product

    def delete(self, product_id: int) -> None:
        """Elimina un producto de la base de datos."""
        product = self.get_or_404(product_id)
        self.products.delete(product)
        self.session.commit()
