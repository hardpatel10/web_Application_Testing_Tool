"""The ``AssessmentHistoryEntry`` model: an append-only assessment activity log."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import AssessmentHistoryEventType

if TYPE_CHECKING:
    from backend.models.assessment import Assessment


class AssessmentHistoryEntry(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One append-only entry in an assessment's activity log.

    Written by the service layer whenever a meaningful lifecycle event
    happens (created, status change, archive/restore, duplicate, target
    added/removed, bulk import). Never updated or deleted once written.
    """

    __tablename__ = "assessment_history_entries"
    __table_args__ = (
        Index("ix_assessment_history_entries_assessment_id_created_at", "assessment_id", "created_at"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[AssessmentHistoryEventType] = mapped_column(
        Enum(AssessmentHistoryEventType, native_enum=False, validate_strings=True, create_constraint=True, length=32),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    assessment: Mapped["Assessment"] = relationship(back_populates="history")
