"""The ``Fingerprint`` model: protocol-level identity evidence.

Distinct from the ``fingerprint`` merge-key *columns* on ``DiscoveredHost``/
``Service``/``Observation`` (see ``backend.services.fingerprinting``) --
those compute deterministic dedup keys ("have I seen this host/service/
observation before"); this table stores *observed protocol evidence*
("what identity signals did I actually capture") -- e.g. an SSH host-key
hash, a TLS certificate's SHA-256, an SMB signing fingerprint. Kept
separate per single-responsibility.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import FingerprintType

if TYPE_CHECKING:
    from backend.models.discovered_host import DiscoveredHost
    from backend.models.service import Service
    from backend.models.tool_execution import ToolExecution


class Fingerprint(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One piece of captured protocol-level identity evidence, scoped to a host and/or a service."""

    __tablename__ = "fingerprints"
    __table_args__ = (
        CheckConstraint("host_id IS NOT NULL OR service_id IS NOT NULL", name="fingerprint_has_owner"),
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
    fingerprint_type: Mapped[FingerprintType] = mapped_column(
        Enum(FingerprintType, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="SET NULL"),
        nullable=True,
    )

    host: Mapped["DiscoveredHost | None"] = relationship()
    service: Mapped["Service | None"] = relationship()
    source_execution: Mapped["ToolExecution | None"] = relationship()
