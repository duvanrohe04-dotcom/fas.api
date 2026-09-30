"""Staff user model."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.columns import created_at_column, updated_at_column


class UserRole(enum.StrEnum):
    """Access levels available in the application."""

    ADMIN = "admin"
    CASHIER = "cajero"
    WAITER = "mesero"


class User(Base):
    """A staff member able to sign in and use the API."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20, validate_strings=True),
        default=UserRole.WAITER,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    def __repr__(self) -> str:
        """Return a readable representation for debugging."""
        return f"<User id={self.id} username={self.username!r} role={self.role}>"
