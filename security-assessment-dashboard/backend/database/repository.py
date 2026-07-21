"""Generic async repository: CRUD, filtering, sorting, and pagination.

Later-phase services depend on this abstraction instead of hand-writing
SQLAlchemy queries per model, keeping query construction in one place and
services testable against a plain interface. The repository never commits
the session — that transaction boundary belongs to the caller (typically
the FastAPI request-scoped session dependency), so a service can compose
several repository calls into one atomic unit of work.
"""

import uuid
from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import ColumnExpressionArgument, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.base import Base
from backend.database.pagination import Page, Pagination, Sort, SortDirection

ModelType = TypeVar("ModelType", bound=Base)


class Repository(Generic[ModelType]):
    """Generic async CRUD repository for a single ORM model type."""

    def __init__(self, session: AsyncSession, model: type[ModelType]) -> None:
        self._session = session
        self._model = model

    async def get(self, id_: uuid.UUID) -> ModelType | None:
        """Fetch one row by primary key, or ``None`` if it doesn't exist."""
        return await self._session.get(self._model, id_)

    async def list(
        self,
        *,
        filters: Sequence[ColumnExpressionArgument[bool]] = (),
        sort: Sequence[Sort] = (),
        pagination: Pagination | None = None,
    ) -> Page[ModelType]:
        """Fetch one page of rows matching ``filters``, ordered by ``sort``."""
        pagination = pagination or Pagination()

        stmt = self._apply_sort(select(self._model).where(*filters), sort)
        stmt = stmt.offset(pagination.offset).limit(pagination.page_size)

        total = await self.count(filters=filters)
        result = await self._session.execute(stmt)

        return Page(
            items=list(result.scalars().all()),
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def count(self, *, filters: Sequence[ColumnExpressionArgument[bool]] = ()) -> int:
        """Count rows matching ``filters``."""
        stmt = select(func.count()).select_from(self._model).where(*filters)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    def _apply_sort(self, stmt: Select[tuple[ModelType]], sort: Sequence[Sort]) -> Select[tuple[ModelType]]:
        for term in sort:
            column = getattr(self._model, term.field)
            stmt = stmt.order_by(column.desc() if term.direction == SortDirection.DESC else column.asc())
        return stmt

    async def create(self, **values: object) -> ModelType:
        """Instantiate, add, and flush a new row, returning it with defaults populated."""
        instance = self._model(**values)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def update(self, instance: ModelType, **values: object) -> ModelType:
        """Apply ``values`` to an already-loaded instance and flush the change."""
        for key, value in values.items():
            setattr(instance, key, value)
        await self._session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete an already-loaded instance and flush the change."""
        await self._session.delete(instance)
        await self._session.flush()
