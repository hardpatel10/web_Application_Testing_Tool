"""The ``ToolExecution`` model: one run of one tool against one target."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import ToolExecutionStatus

if TYPE_CHECKING:
    from backend.models.assessment import Assessment
    from backend.models.execution_host import ExecutionHost
    from backend.models.execution_observation import ExecutionObservation
    from backend.models.finding import Finding
    from backend.models.raw_tool_output import RawToolOutput
    from backend.models.target import Target
    from backend.models.tool import Tool


class ToolExecution(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One execution of one tool against one target within an assessment -- one job.

    ``assessment_id`` is denormalized onto this table (in addition to the
    implicit assessment via ``target_id``) so executions can be queried and
    cascade-deleted per-assessment without a join through ``targets``.

    ``created_at`` (added in Phase 6, alongside the execution engine) is
    when the job was *planned* -- distinct from ``started_at``, since a
    job routinely sits ``PENDING``/``QUEUED`` for a while before a worker
    slot actually picks it up. Needed for a stable, meaningful default
    sort order in job history/listing views.
    """

    __tablename__ = "tool_executions"
    __table_args__ = (
        Index("ix_tool_executions_assessment_id_status", "assessment_id", "status"),
        Index("ix_tool_executions_target_id_tool_id", "target_id", "tool_id"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[ToolExecutionStatus] = mapped_column(
        Enum(ToolExecutionStatus, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        default=ToolExecutionStatus.PENDING,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    stderr_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    log_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Human-readable detail: skip reason, failure/timeout/cancellation cause."
    )
    profile_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Scan profile id used to build the command (Phase 7), if the tool supports profiles."
    )
    generated_command: Mapped[list | None] = mapped_column(
        JSON, nullable=True, doc="The actual argv built by the plugin's build_command(), for audit/display."
    )
    advanced_options: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, doc="User overrides (timing/ports/verbosity/etc.) applied on top of the profile."
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="tool_executions")
    target: Mapped["Target"] = relationship(back_populates="tool_executions")
    tool: Mapped["Tool"] = relationship(back_populates="executions")
    raw_outputs: Mapped[list["RawToolOutput"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan", passive_deletes=True
    )
    #: Findings this execution most recently (re-)confirmed -- the findings
    #: themselves belong to the Assessment/DiscoveredHost (see backend.models.finding),
    #: not to this execution, so deleting a job's history never deletes a
    #: still-valid finding (SET NULL on Finding.source_execution_id).
    findings: Mapped[list["Finding"]] = relationship(back_populates="source_execution")
    #: Which hosts/observations *this* execution touched (created or re-confirmed) --
    #: the hosts/observations themselves belong to the Target/Assessment (see
    #: backend.models.discovered_host/observation), not to this execution, so
    #: deleting a job only removes its link rows here, never the durable inventory itself.
    execution_hosts: Mapped[list["ExecutionHost"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan", passive_deletes=True
    )
    execution_observations: Mapped[list["ExecutionObservation"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan", passive_deletes=True
    )
