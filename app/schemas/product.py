from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    """Campos comunes de un producto."""

    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    price: float = Field(gt=0)
    category_id: int


class ProductCreate(ProductBase):
    """Datos para crear un producto."""

    stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    """Datos para actualizar un producto. Todos los campos son opcionales."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    category_id: int | None = None
    is_active: bool | None = None


class ProductRead(ProductBase):
    """Producto devuelto por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stock: int
    is_active: bool


class ProductStockUpdate(BaseModel):
    """Ajuste de stock: una cantidad absoluta o un delta."""

    stock: int | None = Field(default=None, ge=0, description="Cantidad absoluta.")
    delta: int | None = Field(
        default=None, description="Cantidad a sumar (puede ser negativa)."
    )
