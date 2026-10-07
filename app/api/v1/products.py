from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AdminUser, CurrentUser, DbSession, StaffUser
from app.schemas.common import Page, PaginationDep
from app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductStockUpdate,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


def get_product_service(session: DbSession) -> ProductService:
    """Devuelve el servicio de productos ligado a la sesión de la petición."""
    return ProductService(session)


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]


@router.get("", response_model=Page[ProductRead], summary="Listar productos (público)")
def list_products(
    pagination: PaginationDep,
    service: ProductServiceDep,
    category_id: Annotated[
        int | None, Query(description="Filtra por categoría.")
    ] = None,
    is_active: Annotated[bool | None, Query(description="Filtra por estado.")] = None,
) -> Page[ProductRead]:
    """
    Devuelve una página de productos, opcionalmente filtrada por categoría y estado.
    """
    return service.list(pagination, category_id=category_id, is_active=is_active)


@router.get("/{product_id}", response_model=ProductRead, summary="Ver un producto")
def get_product(
    product_id: int, service: ProductServiceDep, _: CurrentUser
) -> ProductRead:
    """
    Devuelve un producto por su id.
    """
    return ProductRead.model_validate(service.get_or_404(product_id))


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto (solo admin)",
)
def create_product(
    payload: ProductCreate, service: ProductServiceDep, _: AdminUser
) -> ProductRead:
    """
    Crea un producto. Requiere token de administrador.
    """
    return ProductRead.model_validate(service.create(payload))


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    summary="Actualizar producto (solo admin)",
)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    service: ProductServiceDep,
    _: AdminUser,
) -> ProductRead:
    """
    Actualiza parcialmente un producto. Requiere token de administrador.
    """
    return ProductRead.model_validate(service.update(product_id, payload))


@router.patch(
    "/{product_id}/stock",
    response_model=ProductRead,
    summary="Ajustar stock (admin o cajero)",
)
def adjust_stock(
    product_id: int,
    payload: ProductStockUpdate,
    service: ProductServiceDep,
    _: StaffUser,
) -> ProductRead:
    """
    Ajusta el stock de forma absoluta (`stock`) o por delta (`delta`).
    """
    return ProductRead.model_validate(service.adjust_stock(product_id, payload))


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar producto (solo admin)",
)
def delete_product(product_id: int, service: ProductServiceDep, _: AdminUser) -> None:
    """
    Elimina un producto. Requiere token de administrador.
    """
    service.delete(product_id)
