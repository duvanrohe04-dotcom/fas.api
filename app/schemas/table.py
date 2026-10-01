from pydantic import BaseModel, ConfigDict, Field

from app.models import TableStatus


class TableCreate(BaseModel):
    """Datos para crear una mesa."""

    number: int = Field(ge=1)
    capacity: int = Field(default=2, ge=1)


class TableUpdate(BaseModel):
    """Datos para actualizar una mesa. Todos los campos son opcionales."""

    capacity: int | None = Field(default=None, ge=1)
    status: TableStatus | None = None


class TableRead(BaseModel):
    """Mesa devuelta por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    capacity: int
    status: TableStatus
