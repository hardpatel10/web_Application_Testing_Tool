"""The ``RawToolOutput`` model: unmodified output captured from a tool run."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import RawOutputFormat

if TYPE_CHECKING:
    from backend.models.tool_execution import ToolExecution


class RawToolOutput(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Original, unmodified output produced by one tool execution.

    Written once and never edited or overwritten by the application —
    every future parser normalizes findings from this data, so it is the
    permanent source of truth for what a tool actually reported.
    """

    __tablename__ = "raw_tool_outputs"
    __table_args__ = (
        CheckConstraint(
            "file_path IS NOT NULL OR raw_text IS NOT NULL",
            name="has_content",
        ),
    )

    execution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format: Mapped[RawOutputFormat] = mapped_column(
        Enum(RawOutputFormat, native_enum=False, validate_strings=True, create_constraint=True, length=8),
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    execution: Mapped["ToolExecution"] = relationship(back_populates="raw_outputs")
