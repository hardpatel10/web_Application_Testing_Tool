"""The ``Observation`` model: a neutral, non-vulnerability fact reported by a scan.

Covers script/plugin output (e.g. an SSL certificate's expiry, SMB signing
being disabled, an SSH host key algorithm list) that is informational, not
a judged vulnerability. Per ``.claude/CLAUDE.md`` and this phase's explicit
instruction: no severity, no CVSS, no confidence rating, no fabricated
findings -- deliberately has no severity/confidence column at all, unlike
``Finding``. ``title``/``detail`` carry the factual description.

Deduplicated across repeated scans via ``fingerprint`` (see
``backend.services.fingerprinting.observation_fingerprint``) when scoped to
a host; a re-observation bumps ``last_seen`` and adds a new
``ObservationEvidence`` row rather than duplicating the observation itself.
An execution-level (not host-specific) observation has ``host_id=None`` and
is never deduplicated -- SQL unique indexes treat NULLs as distinct, so this
is an accepted limitation rather than a bug (execution-level observations
with no host are rare; nearly every NSE host/port script observation has one).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import ObservationCategory

if TYPE_CHECKING:
    from backend.models.discovered_host import DiscoveredHost
    from backend.models.observation_evidence import ObservationEvidence
    from backend.models.service import Service
    from backend.models.tool_execution import ToolExecution


class Observation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One neutral, descriptive fact -- not a vulnerability -- from a tool execution."""

    __tablename__ = "observations"
    __table_args__ = (
        Index("uq_observations_host_id_fingerprint", "host_id", "fingerprint", unique=True),
    )

    #: Denormalized "most recently observed by" pointer -- full history lives in
    #: ExecutionObservation. Nullable + SET NULL because this observation belongs
    #: to the DiscoveredHost now, not to any one execution; deleting an old job
    #: must never delete a still-valid, still-current observation.
    execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discovered_hosts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plugin: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True, doc="Originating tool, e.g. 'nmap'. Denormalized for filtering."
    )
    source: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Originating script/plugin id, e.g. 'ssl-cert', 'smb-security-mode'."
    )
    category: Mapped[ObservationCategory] = mapped_column(
        Enum(ObservationCategory, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        default=ObservationCategory.OTHER,
    )
    observation_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Free-text, e.g. 'open_port'/'http_header'/'smb_signing_disabled' -- not an enum, new plugins keep inventing new types.",
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Deterministic merge key from backend.services.fingerprinting.observation_fingerprint.
    fingerprint: Mapped[str] = mapped_column(String(80), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    execution: Mapped["ToolExecution | None"] = relationship()
    host: Mapped["DiscoveredHost | None"] = relationship(back_populates="observations")
    service: Mapped["Service | None"] = relationship()
    evidence: Mapped[list["ObservationEvidence"]] = relationship(
        back_populates="observation", cascade="all, delete-orphan", passive_deletes=True
    )
