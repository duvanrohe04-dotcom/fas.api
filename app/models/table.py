import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order


class TableStatus(str, enum.Enum):
    AVAILABLE = "disponible"
    OCCUPIED = "ocupada"


class Table(Base, TimestampMixin):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    number: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False
    )
    capacity: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    status: Mapped[TableStatus] = mapped_column(
        Enum(TableStatus), default=TableStatus.AVAILABLE, nullable=False
    )

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="table")
