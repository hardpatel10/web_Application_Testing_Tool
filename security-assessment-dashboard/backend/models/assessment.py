"""The ``Assessment`` model: the root aggregate of a security engagement."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from backend.models.enums import AssessmentStatus, AssessmentType

if TYPE_CHECKING:
    from backend.models.analyst_note import AnalystNote
    from backend.models.assessment_history import AssessmentHistoryEntry
    from backend.models.assessment_tag import AssessmentTag
    from backend.models.assessment_tool import AssessmentTool
    from backend.models.attachment import Attachment
    from backend.models.discovered_host import DiscoveredHost
    from backend.models.finding import Finding
    from backend.models.report import Report
    from backend.models.target import Target
    from backend.models.tool_execution import ToolExecution


class Assessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One security assessment engagement.

    The root aggregate that every target, tool run, finding, note, report,
    and attachment is ultimately scoped to. Deleting an assessment cascades
    to all of its owned data.

    ``deleted_at`` is a soft-delete marker, deliberately separate from
    ``status``: per project requirements, deleting an assessment through
    the API must never remove its on-disk data or its database row, only
    hide it from the default view. Archiving (``status == ARCHIVED``) is
    a distinct, restorable workflow state.
    """

    __tablename__ = "assessments"
    __table_args__ = (
        Index("ix_assessments_status_created_at", "status", "created_at"),
        Index(
            "uq_assessments_name_active",
            "name",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment_type: Mapped[AssessmentType] = mapped_column(
        Enum(AssessmentType, native_enum=False, validate_strings=True, create_constraint=True, length=32),
        nullable=False,
    )
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(AssessmentStatus, native_enum=False, validate_strings=True, create_constraint=True, length=32),
        nullable=False,
        default=AssessmentStatus.DRAFT,
        index=True,
    )
    previous_status: Mapped[AssessmentStatus | None] = mapped_column(
        Enum(AssessmentStatus, native_enum=False, validate_strings=True, create_constraint=True, length=32),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    tags: Mapped[list["AssessmentTag"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
    history: Mapped[list["AssessmentHistoryEntry"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
    targets: Mapped[list["Target"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
    assessment_tools: Mapped[list["AssessmentTool"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
    discovered_hosts: Mapped[list["DiscoveredHost"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
    notes: Mapped[list["AnalystNote"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
