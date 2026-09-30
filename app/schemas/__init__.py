"""Pydantic schemas for the API."""

from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import ErrorResponse, IdResponse, Message, Page
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.schemas.order import (
    KitchenOrderRead,
    OrderCancel,
    OrderCreate,
    OrderItemCreate,
    OrderItemRead,
    OrderRead,
    OrderStatusUpdate,
    OrderSummaryRead,
)
from app.schemas.product import ProductCreate, ProductRead, ProductStockUpdate, ProductUpdate
from app.schemas.table import TableCreate, TableRead, TableUpdate

__all__ = [
    "CategoryCreate",
    "CategoryRead",
    "CategoryUpdate",
    "CustomerCreate",
    "CustomerRead",
    "CustomerUpdate",
    "ErrorResponse",
    "IdResponse",
    "KitchenOrderRead",
    "Message",
    "OrderCancel",
    "OrderCreate",
    "OrderItemCreate",
    "OrderItemRead",
    "OrderRead",
    "OrderStatusUpdate",
    "OrderSummaryRead",
    "Page",
    "ProductCreate",
    "ProductRead",
    "ProductStockUpdate",
    "ProductUpdate",
    "TableCreate",
    "TableRead",
    "TableUpdate",
]
