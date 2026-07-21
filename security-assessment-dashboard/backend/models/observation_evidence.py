"""The ``ObservationEvidence`` model: raw evidence backing an observation.

Directly mirrors the existing, already-battle-tested ``FindingEvidence``
pattern (``backend.models.finding``): append-only, never overwritten. Each
re-observation across a re-scan adds a *new* evidence row rather than
replacing the old one -- per the phase's explicit "never overwrite evidence."
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.models.observation import Observation


class ObservationEvidence(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One piece of raw evidence (XML/JSON fragment, script output, header, response, cert) for an observation."""

    __tablename__ = "observation_evidence"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("observations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_tool: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True, doc="For large evidence, e.g. a full cert PEM.")

    observation: Mapped["Observation"] = relationship(back_populates="evidence")
