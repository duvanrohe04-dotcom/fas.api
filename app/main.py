"""FastAPI application factory and entry point."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging

settings = get_settings()
logger = logging.getLogger(__name__)

DESCRIPTION = """
Backend de la cafetería: catálogo, pedidos, pagos y reportes.

* **Autenticación**: `POST /api/v1/auth/login` entrega un token Bearer.
* **Roles**: `admin`, `cajero` y `mesero`.
* **Errores**: siempre en el formato `{"error": {"code", "message", "details"}}`.
"""

TAGS_METADATA: list[dict[str, Any]] = [
    {"name": "Health", "description": "Estado del servicio y sus dependencias."},
    {"name": "Auth", "description": "Inicio de sesión, tokens y perfil del usuario."},
    {"name": "Categorías", "description": "Catálogo de categorías del menú."},
    {"name": "Productos", "description": "Artículos del menú con precio y control de stock."},
    {"name": "Clientes", "description": "Registro de clientes de la cafetería."},
    {"name": "Mesas", "description": "Mesas del local y su disponibilidad."},
    {"name": "Pedidos", "description": "Creación de pedidos y gestión de su estado."},
    {"name": "Pagos", "description": "Cobros asociados a un pedido."},
    {"name": "Reportes", "description": "Indicadores de ventas, productos y stock."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure logging on startup and log the shutdown."""
    setup_logging()
    logger.info(
        "Starting application",
        extra={"environment": settings.ENVIRONMENT, "version": settings.VERSION},
    )
    yield
    logger.info("Application stopped")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        description=DESCRIPTION,
        version=settings.VERSION,
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "Equipo de la cafetería"},
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.middleware("http")(request_logging_middleware)

    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)
    application.include_router(api_router, prefix="", include_in_schema=False)
    return application


async def request_logging_middleware(request: Request, call_next: Any) -> Any:
    """Log method, path, status and duration for every request."""
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "%s %s -> %s in %sms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app = create_app()
