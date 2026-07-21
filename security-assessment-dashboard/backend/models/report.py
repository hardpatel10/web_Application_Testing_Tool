"""The ``Report`` model: a generated report artifact for an assessment."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import UUIDPrimaryKeyMixin, utcnow
from backend.models.enums import ReportType

if TYPE_CHECKING:
    from backend.models.assessment import Assessment


class Report(UUIDPrimaryKeyMixin, Base):
    """A generated report file for an assessment.

    Produced by the reporting layer (a later phase) from an assessment's
    findings; this table only records the resulting artifact's metadata
    and on-disk location.
    """

    __tablename__ = "reports"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type: Mapped[ReportType] = mapped_column(
        Enum(ReportType, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="reports")
