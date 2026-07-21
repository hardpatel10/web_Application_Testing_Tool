"""The ``Target`` model: one scan target within an assessment."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from backend.models.enums import TargetType

if TYPE_CHECKING:
    from backend.models.assessment import Assessment
    from backend.models.discovered_host import DiscoveredHost
    from backend.models.tool_execution import ToolExecution


class Target(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single scan target (IP, CIDR range, hostname, domain, or URL).

    Belongs to exactly one assessment. Deleting the owning assessment
    deletes the target and, transitively, its executions.
    """

    __tablename__ = "targets"
    __table_args__ = (
        Index("uq_targets_assessment_id_target_value", "assessment_id", "target_value", unique=True),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[TargetType] = mapped_column(
        Enum(TargetType, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
    )
    target_value: Mapped[str] = mapped_column(String(512), nullable=False)
    resolved_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    assessment: Mapped["Assessment"] = relationship(back_populates="targets")
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        back_populates="target", cascade="all, delete-orphan", passive_deletes=True
    )
    discovered_hosts: Mapped[list["DiscoveredHost"]] = relationship(
        back_populates="target", cascade="all, delete-orphan", passive_deletes=True
    )
