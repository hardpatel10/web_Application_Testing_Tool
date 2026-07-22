"""The ``Target`` model: one scan target within an assessment."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from backend.models.enums import TargetOrigin, TargetType

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
    origin: Mapped[TargetOrigin] = mapped_column(
        Enum(TargetOrigin, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        default=TargetOrigin.USER,
        doc="'pipeline' for a synthetic endpoint the Pipeline Engine generated (e.g. 'http://host:80') -- "
        "excluded from the user-facing Targets tab/picker, but a real Target row in every other respect.",
    )
    discovered_from_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="SET NULL"),
        nullable=True,
        doc="The recon execution (e.g. an Nmap job) whose discovered services this target was generated from.",
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="targets")
    # foreign_keys is required now that Target has a *second* FK to tool_executions
    # (discovered_from_execution_id, above) -- without it, SQLAlchemy can no longer infer
    # which of the two columns this relationship (ToolExecution.target_id's reverse side) should join on.
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        back_populates="target", cascade="all, delete-orphan", passive_deletes=True,
        foreign_keys="ToolExecution.target_id",
    )
    discovered_hosts: Mapped[list["DiscoveredHost"]] = relationship(
        back_populates="target", cascade="all, delete-orphan", passive_deletes=True
    )
