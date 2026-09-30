"""User data access layer."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    """Queries needed by the authentication service."""

    def __init__(self, session: Session) -> None:
        """Store the database session."""
        self.session = session

    def get(self, user_id: int) -> User | None:
        """Fetch a user by primary key."""
        return self.session.get(User, user_id)

    def get_by_identifier(self, identifier: str) -> User | None:
        """Fetch a user by username or email, case insensitively."""
        normalized = identifier.strip().lower()
        return self.session.execute(
            select(User).where(
                or_(func.lower(User.username) == normalized, func.lower(User.email) == normalized)
            )
        ).scalar_one_or_none()

    def create(
        self,
        *,
        username: str,
        email: str,
        full_name: str,
        hashed_password: str,
        role: str,
    ) -> User:
        """Persist a new user and return it."""
        user = User(
            username=username,
            email=email.lower(),
            full_name=full_name,
            hashed_password=hashed_password,
            role=role,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def count(self) -> int:
        """Count the registered users."""
        return self.session.execute(select(func.count(User.id))).scalar_one()
