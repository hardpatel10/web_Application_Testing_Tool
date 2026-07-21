"""The ``Attachment`` model: a general file uploaded to an assessment."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.models.assessment import Assessment


class Attachment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A general-purpose file attached to an assessment (screenshot, PoC, etc.)."""

    __tablename__ = "attachments"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)

    assessment: Mapped["Assessment"] = relationship(back_populates="attachments")
