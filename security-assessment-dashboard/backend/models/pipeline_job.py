"""The ``PipelineJob`` model: one node in one ``PipelineRun``'s execution graph.

A fixed 3-tier shape (``PipelineStage``: recon -> scan -> correlate), not a
generic dependency graph -- that's the Assessment Pipeline's actual shape,
per its own brief. A ``scan``-stage row either carries a real ``execution_id``
(a follow-up scanner the Pipeline Decision Engine actually scheduled) or is a
pure ``SKIPPED`` record with no execution at all (a reserved-for-a-future-
phase scanner, or "no supported web services discovered") -- both are real
rows so the execution graph can render them identically either way.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import PipelineJobStatus, PipelineStage

if TYPE_CHECKING:
    from backend.models.discovered_host import DiscoveredHost
    from backend.models.pipeline_run import PipelineRun
    from backend.models.service import Service
    from backend.models.tool_execution import ToolExecution


class PipelineJob(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One graph node: a recon/scan/correlate step of one ``PipelineRun``."""

    __tablename__ = "pipeline_jobs"

    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
    )
    tool_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Null for a skip node with no specific reserved tool (e.g. the 'correlate' node)."
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("discovered_hosts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )
    execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="The real ToolExecution once scheduled -- null while WAITING for a decision or if SKIPPED.",
    )
    target_value: Mapped[str | None] = mapped_column(
        String(512), nullable=True, doc="The generated endpoint this node targets (e.g. 'http://host:80')."
    )
    status: Mapped[PipelineJobStatus] = mapped_column(
        Enum(PipelineJobStatus, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        default=PipelineJobStatus.WAITING,
    )
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    pipeline_run: Mapped["PipelineRun"] = relationship(back_populates="jobs")
    host: Mapped["DiscoveredHost | None"] = relationship()
    service: Mapped["Service | None"] = relationship()
    execution: Mapped["ToolExecution | None"] = relationship(foreign_keys=[execution_id])
