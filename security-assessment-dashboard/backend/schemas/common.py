"""Shared response schemas."""

from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.database.pagination import Page

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    """A single page of results plus pagination metadata."""

    items: list[T]
    total: int = Field(description="Total number of matching rows across all pages.")
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def from_page(cls, page: "Page[T]") -> "PageResponse[T]":
        """Build a response schema from a :class:`backend.database.pagination.Page`."""
        return cls(items=page.items, total=page.total, page=page.page, page_size=page.page_size, total_pages=page.total_pages)
