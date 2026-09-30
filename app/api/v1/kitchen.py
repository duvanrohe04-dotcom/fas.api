"""Kitchen board endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.auth_deps import StaffUser
from app.api.deps import OrderServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.order import KitchenOrderRead

router = APIRouter(prefix="/kitchen", tags=["kitchen"])

FORBIDDEN = {403: {"model": ErrorResponse, "description": "Rol sin permisos"}}


@router.get(
    "/board",
    summary="Tablero de cocina",
    description=(
        "Devuelve los pedidos en preparación o listos, del más antiguo al más nuevo, "
        "con las líneas que debe preparar la cocina."
    ),
    response_model=list[KitchenOrderRead],
    responses={200: {"description": "Pedidos pendientes de cocina"}, **FORBIDDEN},
)
def kitchen_board(
    service: OrderServiceDep,
    current_user: StaffUser,
) -> list[KitchenOrderRead]:
    """Return the kitchen board."""
    return [KitchenOrderRead.from_model(order) for order in service.kitchen_board()]
