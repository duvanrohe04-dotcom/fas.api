"""Shared schemas: pagination, sorting and error payloads."""

from __future__ import annotations

from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

DEFAULT_PAGE = 1
DEFAULT_SORT = "created_at"


class PageParams(BaseModel):
    """Validated pagination, filtering and sorting parameters."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=DEFAULT_PAGE, ge=1, description="Página solicitada, desde 1.")
    size: int = Field(default=20, ge=1, le=100, description="Elementos por página (máx. 100).")
    search: str | None = Field(
        default=None,
        max_length=120,
        description="Búsqueda parcial por nombre.",
    )
    sort_by: str = Field(default=DEFAULT_SORT, description="Campo de ordenamiento.")
    sort_dir: Literal["asc", "desc"] = Field(
        default="desc",
        description="Dirección del ordenamiento.",
    )

    @property
    def offset(self) -> int:
        """Number of rows to skip for the requested page."""
        return (self.page - 1) * self.size


class Page(BaseModel, Generic[T]):
    """Envelope returned by every paginated endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[T] = Field(default_factory=list, description="Elementos de la página actual.")
    total: int = Field(description="Total de elementos que cumplen el filtro.")
    page: int = Field(description="Página actual.")
    size: int = Field(description="Elementos por página.")
    pages: int = Field(description="Número total de páginas.")
    has_next: bool = Field(description="Indica si existe una página siguiente.")
    has_prev: bool = Field(description="Indica si existe una página anterior.")


class Message(BaseModel):
    """Simple acknowledgement message."""

    detail: str = Field(description="Mensaje describing el resultado de la operación.")


class ErrorDetail(BaseModel):
    """Body of the error envelope used by every failure."""

    code: str = Field(description="Código estable del error.")
    message: str = Field(description="Descripción legible del error.")
    details: Any = Field(default=None, description="Información adicional del error.")


class ErrorResponse(BaseModel):
    """Consistent error envelope."""

    error: ErrorDetail = Field(description="Detalle del error.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "not_found",
                    "message": "Producto 42 no encontrado",
                    "details": None,
                }
            }
        }
    )


class IdResponse(BaseModel):
    """Payload used by delete endpoints."""

    id: int = Field(description="Identificador eliminado.")
    detail: str = Field(default="Eliminado correctamente", description="Mensaje de confirmación.")


PageNumber = Annotated[int, Field(ge=1, description="Número de página, empezando en 1.")]
PageSize = Annotated[int, Field(ge=1, le=100, description="Cantidad de elementos por página.")]
