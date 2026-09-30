"""Dining table endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.auth_deps import CashierUser, StaffUser
from app.api.deps import PaginationParams, TableServiceDep
from app.schemas.common import ErrorResponse, IdResponse, Page
from app.schemas.table import TableCreate, TableRead, TableUpdate

router = APIRouter(prefix="/tables", tags=["tables"])

FORBIDDEN = {403: {"model": ErrorResponse, "description": "Rol sin permisos"}}
NOT_FOUND = {404: {"model": ErrorResponse, "description": "La mesa no existe"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "El número de mesa está en uso"}}
VALIDATION = {422: {"model": ErrorResponse, "description": "Datos inválidos"}}


@router.get(
    "",
    summary="Listar mesas",
    description="Devuelve las mesas con su estado de ocupación.",
    response_model=Page[TableRead],
    responses={200: {"description": "Página de mesas"}, **FORBIDDEN},
)
def list_tables(
    service: TableServiceDep,
    current_user: StaffUser,
    pagination: PaginationParams,
    is_active: Annotated[
        bool | None, Query(description="Filtra por mesas activas o inactivas.")
    ] = None,
    is_occupied: Annotated[
        bool | None,
        Query(description="Filtra por mesas con pedido abierto o libres."),
    ] = None,
) -> Page[TableRead]:
    """List tables marking the occupied ones."""
    page = service.list(pagination, is_active=is_active, is_occupied=is_occupied)
    return Page[TableRead](
        items=[TableRead.from_model(item) for item in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
        pages=page.pages,
        has_next=page.has_next,
        has_prev=page.has_prev,
    )


@router.post(
    "",
    summary="Registrar mesa",
    description="Crea una mesa. El número no puede estar repetido.",
    response_model=TableRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Mesa creada"},
        **FORBIDDEN,
        **CONFLICT,
        **VALIDATION,
    },
)
def create_table(
    payload: TableCreate,
    service: TableServiceDep,
    current_user: CashierUser,
) -> TableRead:
    """Create a table."""
    table = service.create(
        number=payload.number,
        name=payload.name,
        capacity=payload.capacity,
        is_active=payload.is_active,
    )
    return TableRead.from_model(table)


@router.get(
    "/{table_id}",
    summary="Obtener mesa",
    description="Devuelve una mesa por su identificador.",
    response_model=TableRead,
    responses={200: {"description": "Mesa encontrada"}, **FORBIDDEN, **NOT_FOUND},
)
def get_table(
    service: TableServiceDep,
    current_user: StaffUser,
    table_id: Annotated[int, Path(ge=1, description="Identificador de la mesa.")],
) -> TableRead:
    """Return a single table."""
    return TableRead.from_model(service.get(table_id))


@router.patch(
    "/{table_id}",
    summary="Actualizar mesa",
    description="Actualiza parcialmente los campos de una mesa.",
    response_model=TableRead,
    responses={
        200: {"description": "Mesa actualizada"},
        **FORBIDDEN,
        **NOT_FOUND,
        **CONFLICT,
        **VALIDATION,
    },
)
def update_table(
    payload: TableUpdate,
    service: TableServiceDep,
    current_user: CashierUser,
    table_id: Annotated[int, Path(ge=1, description="Identificador de la mesa.")],
) -> TableRead:
    """Update a table partially."""
    table = service.update(
        table_id,
        number=payload.number,
        name=payload.name,
        capacity=payload.capacity,
        is_active=payload.is_active,
    )
    return TableRead.from_model(table)


@router.delete(
    "/{table_id}",
    summary="Eliminar mesa",
    description="Elimina una mesa. No es posible si tiene un pedido abierto.",
    response_model=IdResponse,
    responses={
        200: {"description": "Mesa eliminada"},
        **FORBIDDEN,
        **NOT_FOUND,
        422: {"model": ErrorResponse, "description": "La mesa tiene un pedido abierto"},
    },
)
def delete_table(
    service: TableServiceDep,
    current_user: CashierUser,
    table_id: Annotated[int, Path(ge=1, description="Identificador de la mesa.")],
) -> IdResponse:
    """Delete a table without open orders."""
    deleted_id = service.delete(table_id)
    return IdResponse(id=deleted_id, detail="Mesa eliminada correctamente")
