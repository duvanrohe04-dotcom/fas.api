"""Product endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.auth_deps import CashierUser, StaffUser
from app.api.deps import PaginationParams, ProductServiceDep
from app.schemas.common import ErrorResponse, IdResponse, Page
from app.schemas.product import ProductCreate, ProductRead, ProductStockUpdate, ProductUpdate

router = APIRouter(prefix="/products", tags=["Productos"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "El producto no existe"}}
FORBIDDEN = {403: {"model": ErrorResponse, "description": "Rol sin permisos"}}


@router.get(
    "",
    summary="Listar productos",
    description=(
        "Devuelve los productos del menú paginados. Permite filtrar por categoría, "
        "buscar por nombre y ordenar por precio, stock o fecha de creación."
    ),
    response_model=Page[ProductRead],
    responses={200: {"description": "Página de productos"}, **FORBIDDEN},
)
def list_products(
    service: ProductServiceDep,
    current_user: StaffUser,
    pagination: PaginationParams,
    category_id: Annotated[
        int | None,
        Query(ge=1, description="Filtra por identificador de categoría."),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filtra por estado activo."),
    ] = None,
    low_stock: Annotated[
        bool | None,
        Query(description="Filtra productos con stock igual o inferior al umbral."),
    ] = None,
) -> Page[ProductRead]:
    """List the menu products."""
    page = service.list(
        pagination,
        category_id=category_id,
        is_active=is_active,
        low_stock=low_stock,
    )
    return Page[ProductRead](
        items=[ProductRead.from_model(item) for item in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
        pages=page.pages,
        has_next=page.has_next,
        has_prev=page.has_prev,
    )


@router.post(
    "",
    summary="Crear producto",
    description="Crea un producto associating it with an existing category.",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Producto creado"},
        **FORBIDDEN,
        404: {"model": ErrorResponse, "description": "La categoría no existe"},
        422: {"model": ErrorResponse, "description": "Datos inválidos"},
    },
)
def create_product(
    payload: ProductCreate,
    service: ProductServiceDep,
    current_user: CashierUser,
) -> ProductRead:
    """Create a new product."""
    product = service.create(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        category_id=payload.category_id,
        stock=payload.stock,
        low_stock_threshold=payload.low_stock_threshold,
        is_active=payload.is_active,
    )
    return ProductRead.from_model(product)


@router.get(
    "/{product_id}",
    summary="Obtener producto",
    description="Devuelve un producto concreto con los datos de su categoría.",
    response_model=ProductRead,
    responses={200: {"description": "Producto encontrado"}, **FORBIDDEN, **NOT_FOUND},
)
def get_product(
    service: ProductServiceDep,
    current_user: StaffUser,
    product_id: Annotated[int, Path(ge=1, description="Identificador del producto.")],
) -> ProductRead:
    """Return a single product."""
    return ProductRead.from_model(service.get(product_id))


@router.patch(
    "/{product_id}",
    summary="Actualizar producto",
    description="Actualiza parcialmente un producto existente (precio, stock, categoría...).",
    response_model=ProductRead,
    responses={
        200: {"description": "Producto actualizado"},
        **FORBIDDEN,
        **NOT_FOUND,
        422: {"model": ErrorResponse, "description": "Datos inválidos"},
    },
)
def update_product(
    payload: ProductUpdate,
    service: ProductServiceDep,
    product_id: Annotated[int, Path(ge=1, description="Identificador del producto.")],
) -> ProductRead:
    """Update a product partially."""
    product = service.update(
        product_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        category_id=payload.category_id,
        stock=payload.stock,
        low_stock_threshold=payload.low_stock_threshold,
        is_active=payload.is_active,
    )
    return ProductRead.from_model(product)


@router.delete(
    "/{product_id}",
    summary="Eliminar producto",
    description="Elimina un producto del menú. No es posible si tiene pedidos asociados.",
    response_model=IdResponse,
    responses={
        200: {"description": "Producto eliminado"},
        **FORBIDDEN,
        **NOT_FOUND,
        409: {"model": ErrorResponse, "description": "El producto tiene pedidos asociados"},
    },
)
def delete_product(
    service: ProductServiceDep,
    product_id: Annotated[int, Path(ge=1, description="Identificador del producto.")],
) -> IdResponse:
    """Delete a product."""
    deleted_id = service.delete(product_id)
    return IdResponse(id=deleted_id, detail="Producto eliminado correctamente")


@router.post(
    "/{product_id}/stock",
    summary="Aumentar stock",
    description="Suma stock al producto, por ejemplo tras una recepción de mercancía.",
    response_model=ProductRead,
    responses={
        200: {"description": "Stock actualizado"},
        **FORBIDDEN,
        **NOT_FOUND,
        422: {"model": ErrorResponse, "description": "Cantidad inválida"},
    },
)
def increase_stock(
    payload: ProductStockUpdate,
    service: ProductServiceDep,
    current_user: CashierUser,
    product_id: Annotated[int, Path(ge=1, description="Identificador del producto.")],
) -> ProductRead:
    """Increase the stock of a product."""
    product = service.adjust_stock(
        product_id,
        quantity=payload.quantity,
        reason=payload.reason,
    )
    return ProductRead.from_model(product)
