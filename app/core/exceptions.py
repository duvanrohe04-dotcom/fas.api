"""Domain exceptions and centralized JSON error handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for every expected application error."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        """Store the message plus optional code, status and details."""
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    """Requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class BusinessRuleError(AppError):
    """A domain rule forbids the operation."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "business_rule_violation"


class ConflictError(AppError):
    """The request conflicts with the current state of the resource."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class AuthenticationError(AppError):
    """Credentials or token are missing or invalid."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"


class PermissionDeniedError(AppError):
    """The authenticated user lacks the required role."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"


class InsufficientStockError(BusinessRuleError):
    """Not enough stock to fulfil a request."""

    code = "insufficient_stock"


def error_body(message: str, code: str, details: Any = None) -> dict[str, dict[str, Any]]:
    """Build the consistent error payload used by every handler."""
    return {"error": {"code": code, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the application."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render an AppError as JSON."""
    assert isinstance(exc, AppError)
    logger.info("Domain error on %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_body(exc.message, exc.code, exc.details)),
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render FastAPI request validation errors as JSON."""
    assert isinstance(exc, RequestValidationError)
    logger.info("Validation error on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(
            error_body("Request validation failed", "validation_error", exc.errors()),
        ),
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render HTTPException as JSON using the same envelope."""
    assert isinstance(exc, StarletteHTTPException)
    code = "not_found" if exc.status_code == 404 else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_body(str(exc.detail), code)),
        headers=getattr(exc, "headers", None),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler that logs and hides internals from clients."""
    logger.exception("Unhandled error on %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body("Internal server error", "internal_error"),
    )
