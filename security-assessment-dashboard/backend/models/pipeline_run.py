"""The ``PipelineRun`` model: one durable history record of one Assessment Pipeline execution.

Mirrors ``backend.models.correlation_run.CorrelationRun``'s role for the
Correlation Engine -- a real, queryable "what did the pipeline do and when"
record, not an ad-hoc in-memory guess. One ``PipelineRun`` is created per
"Start Assessment" pipeline trigger and owns every ``PipelineJob`` node in
that run's execution graph (see ``backend.models.pipeline_job``).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import PipelineRunStatus

if TYPE_CHECKING:
    from backend.models.assessment import Assessment
    from backend.models.pipeline_job import PipelineJob
    from backend.models.tool_execution import ToolExecution


class PipelineRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One invocation of the Assessment Pipeline, scoped to one assessment."""

    __tablename__ = "pipeline_runs"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recon_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="SET NULL"),
        nullable=True,
        doc="The Nmap job seeding this run's decisions.",
    )
    status: Mapped[PipelineRunStatus] = mapped_column(
        Enum(PipelineRunStatus, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        default=PipelineRunStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assessment: Mapped["Assessment"] = relationship()
    recon_execution: Mapped["ToolExecution | None"] = relationship(foreign_keys=[recon_execution_id])
    jobs: Mapped[list["PipelineJob"]] = relationship(
        back_populates="pipeline_run", cascade="all, delete-orphan", passive_deletes=True
    )
