"""Shared mixins for ORM models.

Every model in this package composes these mixins rather than declaring
``id``/timestamp columns by hand, so the primary-key strategy and UTC
timestamp behavior stay identical across the schema.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC ``datetime``."""
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key column named ``id``.

    Uses SQLAlchemy's cross-dialect :class:`~sqlalchemy.Uuid` type, which
    maps to a native ``UUID`` column on PostgreSQL and a ``CHAR(32)`` hex
    column on SQLite, keeping both backends compatible with the same model.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class CreatedAtMixin:
    """Adds an immutable ``created_at`` UTC timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


class TimestampMixin(CreatedAtMixin):
    """Adds ``created_at`` and an auto-updating ``updated_at`` UTC timestamp."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
