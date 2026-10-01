from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    """Campos comunes de una categoría."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class CategoryCreate(CategoryBase):
    """Datos para crear una categoría."""


class CategoryUpdate(BaseModel):
    """Datos para actualizar una categoría. Todos los campos son opcionales."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class CategoryRead(CategoryBase):
    """Categoría devuelta por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
