"""Pagination, filtering and sorting helpers shared by repositories."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute

from app.schemas.common import Page


@dataclass(frozen=True, slots=True)
class ListQuery:
    """Normalised list parameters coming from the API layer."""

    page: int = 1
    size: int = 20
    search: str | None = None
    sort_by: str = "id"
    sort_dir: str = "asc"

    @property
    def offset(self) -> int:
        """Number of rows to skip for the requested page."""
        return (self.page - 1) * self.size


def get_ordered_column(statement: Select[Any], sort_by: str) -> InstrumentedAttribute[Any]:
    """Resolve the sort column, defaulting to the primary key when unknown."""
    entity = statement.column_descriptions[0]["entity"]
    column = getattr(entity, sort_by, None)
    if column is None or not hasattr(column, "asc"):
        return entity.id
    return column


def apply_ordering(statement: Select[Any], query: ListQuery) -> Select[Any]:
    """Order a select statement by the requested column and direction.

    The primary key is always appended as a tiebreaker so that pages are
    deterministic when the sort column repeats.
    """
    column = get_ordered_column(statement, query.sort_by)
    orderings = [column.desc() if query.sort_dir == "desc" else column.asc()]
    entity = statement.column_descriptions[0]["entity"]
    if column.key != entity.id.key:
        orderings.append(entity.id.asc())
    return statement.order_by(*orderings)


def apply_pagination(statement: Select[Any], query: ListQuery) -> Select[Any]:
    """Apply ordering, offset and limit to a select statement."""
    return apply_ordering(statement, query).offset(query.offset).limit(query.size)


def apply_search(statement: Select[Any], query: ListQuery, *columns: Any) -> Select[Any]:
    """Apply a case insensitive partial search over the given columns."""
    if not query.search or not columns:
        return statement
    pattern = f"%{query.search.strip().lower()}%"
    conditions = [func.lower(func.coalesce(column, "")).like(pattern) for column in columns]
    return statement.where(or_(*conditions))


def count_statement(statement: Select[Any]) -> Select[int]:
    """Build a count query from a select statement."""
    return select(func.count()).select_from(statement.order_by(None).subquery())


def build_page(items: list[Any], total: int, query: ListQuery) -> Page[Any]:
    """Wrap a list of items and its total into a paginated envelope."""
    pages = math.ceil(total / query.size) if query.size else 0
    return Page[Any](
        items=items,
        total=total,
        page=query.page,
        size=query.size,
        pages=pages,
        has_next=query.page < pages,
        has_prev=query.page > 1,
    )
