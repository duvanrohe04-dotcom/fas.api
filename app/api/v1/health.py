"""Health check endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import database_health_dependency

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Estado del servicio",
    description="Comprueba que la aplicación y la base de datos responden correctamente.",
    response_description="Estado del servicio y sus dependencias",
    response_model=None,
    responses={200: {"description": "Servicio operativo"}, 503: {"description": "Degradado"}},
)
def health_check(
    database_up: Annotated[bool, Depends(database_health_dependency)],
) -> dict[str, Any] | JSONResponse:
    """Report application and database status."""
    settings = get_settings()
    payload = {
        "status": "ok" if database_up else "degraded",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "up" if database_up else "down",
    }
    if database_up:
        return payload
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
