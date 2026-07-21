"""Pagination and sorting primitives for the database layer.

Kept separate from :mod:`backend.database.repository` so the query-shaping
value objects can be reused (e.g. parsed straight from request query
params in a later phase) without importing the repository implementation.
"""

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

T = TypeVar("T")


class SortDirection(StrEnum):
    """Direction to sort a query by."""

    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class Sort:
    """One ``ORDER BY`` term: a model attribute name and a direction."""

    field: str
    direction: SortDirection = SortDirection.ASC


@dataclass(frozen=True, slots=True)
class Pagination:
    """A requested page: 1-indexed page number and page size."""

    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if self.page_size < 1:
            raise ValueError("page_size must be >= 1")

    @property
    def offset(self) -> int:
        """Row offset for this page, for use in ``OFFSET``."""
        return (self.page - 1) * self.page_size


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    """One page of results plus enough metadata to render pagination controls."""

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return math.ceil(self.total / self.page_size) if self.page_size else 0
