from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import Page, PaginationDep
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


def get_category_service(session: DbSession) -> CategoryService:
    """Devuelve el servicio de categorías ligado a la sesión de la petición."""
    return CategoryService(session)


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


@router.get("", response_model=Page[CategoryRead], summary="Listar categorías")
def list_categories(
    pagination: PaginationDep, service: CategoryServiceDep, _: CurrentUser
) -> Page[CategoryRead]:
    """
    Devuelve una página de categorías ordenadas alfabéticamente.
    """
    return service.list(pagination)


@router.get("/{category_id}", response_model=CategoryRead, summary="Ver una categoría")
def get_category(
    category_id: int, service: CategoryServiceDep, _: CurrentUser
) -> CategoryRead:
    """
    Devuelve una categoría por su id.
    """
    return CategoryRead.model_validate(service.get_or_404(category_id))


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear categoría (solo admin)",
)
def create_category(
    payload: CategoryCreate, service: CategoryServiceDep, _: AdminUser
) -> CategoryRead:
    """
    Crea una categoría. Requiere token de administrador.
    """
    return CategoryRead.model_validate(service.create(payload))


@router.patch(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Actualizar categoría (solo admin)",
)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    service: CategoryServiceDep,
    _: AdminUser,
) -> CategoryRead:
    """
    Actualiza parcialmente una categoría. Requiere token de administrador.
    """
    return CategoryRead.model_validate(service.update(category_id, payload))


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar categoría (solo admin)",
)
def delete_category(
    category_id: int, service: CategoryServiceDep, _: AdminUser
) -> None:
    """
    Elimina una categoría. Falla si tiene productos activos asociados.
    """
    service.delete(category_id)
