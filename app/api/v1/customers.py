"""Customer endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.auth_deps import CashierUser, StaffUser
from app.api.deps import CustomerServiceDep, PaginationParams
from app.schemas.common import ErrorResponse, IdResponse, Page
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])

FORBIDDEN = {403: {"model": ErrorResponse, "description": "Rol sin permisos"}}
NOT_FOUND = {404: {"model": ErrorResponse, "description": "El cliente no existe"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "Email o teléfono duplicado"}}
VALIDATION = {422: {"model": ErrorResponse, "description": "Datos inválidos"}}


@router.get(
    "",
    summary="Listar clientes",
    description="Devuelve los clientes registrados con paginación, búsqueda y filtros.",
    response_model=Page[CustomerRead],
    responses={200: {"description": "Página de clientes"}, **FORBIDDEN},
)
def list_customers(
    service: CustomerServiceDep,
    current_user: StaffUser,
    pagination: PaginationParams,
) -> Page[CustomerRead]:
    """List customers."""
    page = service.list(pagination)
    return Page[CustomerRead](
        items=[CustomerRead.from_model(item) for item in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
        pages=page.pages,
        has_next=page.has_next,
        has_prev=page.has_prev,
    )


@router.post(
    "",
    summary="Registrar cliente",
    description="Crea un cliente. El email y el teléfono no pueden estar repetidos.",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Cliente creado"},
        **FORBIDDEN,
        **CONFLICT,
        **VALIDATION,
    },
)
def create_customer(
    payload: CustomerCreate,
    service: CustomerServiceDep,
    current_user: CashierUser,
) -> CustomerRead:
    """Create a customer."""
    customer = service.create(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        is_active=payload.is_active,
    )
    return CustomerRead.from_model(customer)


@router.get(
    "/{customer_id}",
    summary="Obtener cliente",
    description="Devuelve un cliente por su identificador.",
    response_model=CustomerRead,
    responses={200: {"description": "Cliente encontrado"}, **FORBIDDEN, **NOT_FOUND},
)
def get_customer(
    service: CustomerServiceDep,
    current_user: StaffUser,
    customer_id: Annotated[int, Path(ge=1, description="Identificador del cliente.")],
) -> CustomerRead:
    """Return a single customer."""
    return CustomerRead.from_model(service.get(customer_id))


@router.patch(
    "/{customer_id}",
    summary="Actualizar cliente",
    description="Actualiza parcialmente los campos de un cliente.",
    response_model=CustomerRead,
    responses={
        200: {"description": "Cliente actualizado"},
        **FORBIDDEN,
        **NOT_FOUND,
        **CONFLICT,
        **VALIDATION,
    },
)
def update_customer(
    payload: CustomerUpdate,
    service: CustomerServiceDep,
    current_user: CashierUser,
    customer_id: Annotated[int, Path(ge=1, description="Identificador del cliente.")],
) -> CustomerRead:
    """Update a customer partially."""
    customer = service.update(
        customer_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        is_active=payload.is_active,
    )
    return CustomerRead.from_model(customer)


@router.delete(
    "/{customer_id}",
    summary="Eliminar cliente",
    description="Elimina un cliente. No es posible si tiene pedidos asociados.",
    response_model=IdResponse,
    responses={
        200: {"description": "Cliente eliminado"},
        **FORBIDDEN,
        **NOT_FOUND,
        422: {"model": ErrorResponse, "description": "El cliente tiene pedidos"},
    },
)
def delete_customer(
    service: CustomerServiceDep,
    current_user: CashierUser,
    customer_id: Annotated[int, Path(ge=1, description="Identificador del cliente.")],
) -> IdResponse:
    """Delete a customer without orders."""
    deleted_id = service.delete(customer_id)
    return IdResponse(id=deleted_id, detail="Cliente eliminado correctamente")
