"""The ``CorrelationRun`` model: one durable history record of one Correlation Engine pass.

Distinct from ``Finding.first_seen``/``.last_seen`` (which track one
finding's own lifecycle): this is the "Track history" requirement applied to
the *engine itself* — real data backing ``GET /correlation/status`` instead
of an ad-hoc "did anything run" guess, and the audit trail of every rule
evaluation pass across every assessment.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import CorrelationRunStatus

if TYPE_CHECKING:
    from backend.models.assessment import Assessment


class CorrelationRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One invocation of the Correlation Engine, scoped to an assessment or the whole install."""

    __tablename__ = "correlation_runs"

    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Null means this run correlated every assessment.",
    )
    status: Mapped[CorrelationRunStatus] = mapped_column(
        Enum(CorrelationRunStatus, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        default=CorrelationRunStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hosts_evaluated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rules_evaluated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment: Mapped["Assessment | None"] = relationship()
