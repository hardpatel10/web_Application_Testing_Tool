"""The ``AssessmentTag`` model: a free-text label on an assessment."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.assessment import Assessment


class AssessmentTag(Base):
    """One tag attached to one assessment.

    Tags are scoped to a single assessment rather than drawn from a shared,
    reusable tag vocabulary — this application has no cross-assessment
    tag management requirement, so a composite-key link table (matching
    the pattern already used by :class:`~backend.models.assessment_tool.AssessmentTool`)
    is sufficient without introducing a speculative standalone ``Tag`` entity.
    """

    __tablename__ = "assessment_tags"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag: Mapped[str] = mapped_column(String(64), primary_key=True)

    assessment: Mapped["Assessment"] = relationship(back_populates="tags")
