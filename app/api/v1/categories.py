"""Category endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.auth_deps import AdminUser, StaffUser
from app.api.deps import CategoryServiceDep, PaginationParams, ProductServiceDep
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import ErrorResponse, IdResponse, Page
from app.schemas.product import ProductRead

router = APIRouter(prefix="/categories", tags=["Categorías"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "La categoría no existe"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "El nombre ya está en uso"}}
FORBIDDEN = {403: {"model": ErrorResponse, "description": "Rol sin permisos"}}


@router.get(
    "",
    summary="Listar categorías",
    description=(
        "Devuelve las categorías del menú paginadas, con búsqueda por nombre y "
        "ordenamiento configurable."
    ),
    response_model=Page[CategoryRead],
    responses={200: {"description": "Página de categorías"}, **FORBIDDEN},
)
def list_categories(
    service: CategoryServiceDep,
    current_user: StaffUser,
    pagination: PaginationParams,
) -> Page[CategoryRead]:
    """List the menu categories."""
    return service.list(pagination)  # type: ignore[return-value]


@router.post(
    "",
    summary="Crear categoría",
    description="Crea una nueva categoría. El `slug` se genera a partir del nombre.",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Categoría creada"},
        409: {"model": ErrorResponse, "description": "Nombre duplicado"},
    },
)
def create_category(
    payload: CategoryCreate,
    service: CategoryServiceDep,
    current_user: AdminUser,
) -> CategoryRead:
    """Create a new category."""
    category = service.create(
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    return CategoryRead.from_model(category)


@router.get(
    "/{category_id}",
    summary="Obtener categoría",
    description="Devuelve una categoría concreta junto con su número de productos.",
    response_model=CategoryRead,
    responses={200: {"description": "Categoría encontrada"}, **NOT_FOUND},
)
def get_category(
    service: CategoryServiceDep,
    current_user: StaffUser,
    category_id: Annotated[int, Path(ge=1, description="Identificador de la categoría.")],
) -> CategoryRead:
    """Return a single category with its product count."""
    category = service.get(category_id)
    return CategoryRead.from_model(
        category,
        product_count=service.product_count(category_id),
    )


@router.patch(
    "/{category_id}",
    summary="Actualizar categoría",
    description="Actualiza parcialmente los campos de una categoría existente.",
    response_model=CategoryRead,
    responses={
        200: {"description": "Categoría actualizada"},
        **FORBIDDEN,
        **NOT_FOUND,
        **CONFLICT,
    },
)
def update_category(
    payload: CategoryUpdate,
    service: CategoryServiceDep,
    current_user: AdminUser,
    category_id: Annotated[int, Path(ge=1, description="Identificador de la categoría.")],
) -> CategoryRead:
    """Update a category partially."""
    category = service.update(
        category_id,
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    return CategoryRead.from_model(category)


@router.delete(
    "/{category_id}",
    summary="Eliminar categoría",
    description="Elimina una categoría. Solo es posible si no tiene productos asociados.",
    response_model=IdResponse,
    responses={
        200: {"description": "Categoría eliminada"},
        **FORBIDDEN,
        **NOT_FOUND,
        422: {"model": ErrorResponse, "description": "La categoría tiene productos"},
    },
)
def delete_category(
    service: CategoryServiceDep,
    current_user: AdminUser,
    category_id: Annotated[int, Path(ge=1, description="Identificador de la categoría.")],
) -> IdResponse:
    """Delete an empty category."""
    deleted_id = service.delete(category_id)
    return IdResponse(id=deleted_id, detail="Categoría eliminada correctamente")


@router.post(
    "/{category_id}/activate",
    summary="Reactivar categoría",
    description="Vuelve a marcar una categoría desactivada como activa.",
    response_model=CategoryRead,
    responses={200: {"description": "Categoría reactivada"}, **FORBIDDEN, **NOT_FOUND},
)
def activate_category(
    service: CategoryServiceDep,
    current_user: AdminUser,
    category_id: Annotated[int, Path(ge=1, description="Identificador de la categoría.")],
) -> CategoryRead:
    """Reactivate a soft-deleted category."""
    category = service.update(category_id, is_active=True)
    return CategoryRead.from_model(category)


@router.get(
    "/{category_id}/products",
    summary="Listar productos de una categoría",
    description="Devuelve los productos que pertenecen a una categoría concreta.",
    response_model=Page[ProductRead],
    responses={200: {"description": "Página de productos"}, **FORBIDDEN, **NOT_FOUND},
)
def list_category_products(
    service: CategoryServiceDep,
    product_service: ProductServiceDep,
    current_user: StaffUser,
    pagination: PaginationParams,
    category_id: Annotated[int, Path(ge=1, description="Identificador de la categoría.")],
) -> Page[ProductRead]:
    """List the products that belong to a category."""
    category = service.get(category_id)
    page = product_service.list(pagination, category_id=category.id)
    return Page[ProductRead](
        items=[ProductRead.from_model(item) for item in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
        pages=page.pages,
        has_next=page.has_next,
        has_prev=page.has_prev,
    )


@router.get(
    "/lookup/by-slug/{slug}",
    summary="Buscar categoría por slug",
    description="Devuelve la categoría cuyo `slug` coincide con el indicado.",
    response_model=CategoryRead,
    responses={200: {"description": "Categoría encontrada"}, **FORBIDDEN, **NOT_FOUND},
)
def get_category_by_slug(
    service: CategoryServiceDep,
    current_user: StaffUser,
    slug: Annotated[str, Path(min_length=1, max_length=80, description="Slug de la categoría.")],
) -> CategoryRead:
    """Return a category identified by its slug."""
    category = service.get_by_slug(slug)
    return CategoryRead.from_model(category)
