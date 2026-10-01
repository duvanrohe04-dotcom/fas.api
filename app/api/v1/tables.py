from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AdminUser, CurrentUser, DbSession, StaffUser
from app.models import TableStatus
from app.schemas.common import Page, PaginationDep
from app.schemas.table import TableCreate, TableRead, TableUpdate
from app.services.table_service import TableService

router = APIRouter(prefix="/tables", tags=["Tables"])


def get_table_service(session: DbSession) -> TableService:
    """Devuelve el servicio de mesas ligado a la sesión de la petición."""
    return TableService(session)


TableServiceDep = Annotated[TableService, Depends(get_table_service)]


@router.get("", response_model=Page[TableRead], summary="Listar mesas")
def list_tables(
    pagination: PaginationDep,
    service: TableServiceDep,
    _: CurrentUser,
    table_status: Annotated[
        TableStatus | None,
        Query(alias="status", description="Filtra por estado de la mesa."),
    ] = None,
    min_capacity: Annotated[
        int | None, Query(ge=1, description="Capacidad mínima.")
    ] = None,
) -> Page[TableRead]:
    """
    Devuelve una página de mesas ordenadas por número.
    """
    return service.list(pagination, status=table_status, min_capacity=min_capacity)


@router.get("/{table_id}", response_model=TableRead, summary="Ver una mesa")
def get_table(table_id: int, service: TableServiceDep, _: CurrentUser) -> TableRead:
    """
    Devuelve una mesa por su id.
    """
    return TableRead.model_validate(service.get_or_404(table_id))


@router.post(
    "",
    response_model=TableRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear mesa (solo admin)",
)
def create_table(
    payload: TableCreate, service: TableServiceDep, _: AdminUser
) -> TableRead:
    """
    Crea una mesa disponible. Requiere token de administrador.
    """
    return TableRead.model_validate(service.create(payload.number, payload.capacity))


@router.patch(
    "/{table_id}",
    response_model=TableRead,
    summary="Actualizar mesa (solo admin)",
)
def update_table(
    table_id: int,
    payload: TableUpdate,
    service: TableServiceDep,
    _: AdminUser,
) -> TableRead:
    """
    Actualiza parcialmente una mesa. Requiere token de administrador.
    """
    return TableRead.model_validate(service.update(table_id, payload))


@router.patch(
    "/{table_id}/status",
    response_model=TableRead,
    summary="Cambiar estado de mesa (admin o cajero)",
)
def set_table_status(
    table_id: int,
    status: TableStatus,
    service: TableServiceDep,
    _: StaffUser,
) -> TableRead:
    """
    Marca la mesa como ocupada o disponible.
    """
    return TableRead.model_validate(service.set_status(table_id, status))


@router.delete(
    "/{table_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar mesa (solo admin)",
)
def delete_table(table_id: int, service: TableServiceDep, _: AdminUser) -> None:
    """
    Elimina una mesa. Falla si tiene pedidos en curso.
    """
    service.delete(table_id)
