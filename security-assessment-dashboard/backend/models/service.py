"""The ``Service`` model: one discovered port/protocol/service on an asset.

Generic and tool-agnostic, like ``DiscoveredHost``. Purely descriptive (port state,
service name, product, version) — no severity or vulnerability judgment.
Deduplicated across repeated scans of the same asset via ``fingerprint``
(see ``backend.services.fingerprinting.service_fingerprint``): a re-scan
updates ``state``/``product``/``version``/``last_seen`` on the existing row
instead of inserting a duplicate — a port flipping open->closed between
scans is a real, worth-recording state change, not a new row.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import NetworkProtocol, PortState

if TYPE_CHECKING:
    from backend.models.discovered_host import DiscoveredHost
    from backend.models.technology import Technology


class Service(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One port/protocol observed on a host, with whatever service info was fingerprinted."""

    __tablename__ = "services"
    __table_args__ = (
        Index("uq_services_host_id_fingerprint", "host_id", "fingerprint", unique=True),
    )

    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discovered_hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[NetworkProtocol] = mapped_column(
        Enum(NetworkProtocol, native_enum=False, validate_strings=True, create_constraint=True, length=8),
        nullable=False,
    )
    state: Mapped[PortState] = mapped_column(
        Enum(PortState, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
    )
    service_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True, doc="Rarely populated by Nmap today; a future plugin field.")
    version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    banner: Mapped[str | None] = mapped_column(Text, nullable=True, doc="Raw banner text, distinct from extra_info.")
    #: Deterministic merge key from backend.services.fingerprinting.service_fingerprint.
    fingerprint: Mapped[str] = mapped_column(String(80), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    host: Mapped["DiscoveredHost"] = relationship(back_populates="services")
    technologies: Mapped[list["Technology"]] = relationship(
        back_populates="service", cascade="all, delete-orphan", passive_deletes=True
    )
