"""The ``AssessmentTool`` model: links tools to assessments."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.assessment import Assessment
    from backend.models.tool import Tool


class AssessmentTool(Base):
    """Association between one assessment and one tool.

    A composite-primary-key join table (rather than a plain many-to-many
    ``Table``) because it carries its own attributes — whether the tool is
    enabled for this assessment and the order it should run in.
    """

    __tablename__ = "assessment_tools"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tool_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tools.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    execution_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    assessment: Mapped["Assessment"] = relationship(back_populates="assessment_tools")
    tool: Mapped["Tool"] = relationship(back_populates="assessment_tools")
