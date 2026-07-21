"""The ``NetworkInterface`` model: every address one asset has.

Nmap (and any future scanner) can report more than one address per host
(dual-stack IPv4+IPv6, multiple NICs) -- ``DiscoveredHost.ipv4``/``ipv6``/``mac_address``
only ever hold the primary/first-seen values for quick access; this table is
the authoritative, non-lossy list of every address a scan actually reported.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import TargetType

if TYPE_CHECKING:
    from backend.models.discovered_host import DiscoveredHost

#: An interface address is always IPv4 or IPv6 -- reuses TargetType's existing
#: values rather than a new single-purpose enum with the same two members.
_ADDRESS_VERSIONS = (TargetType.IPV4, TargetType.IPV6)


class NetworkInterface(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One address reported for one discovered host."""

    __tablename__ = "network_interfaces"
    __table_args__ = (
        Index("uq_network_interfaces_host_id_ip_address", "host_id", "ip_address", unique=True),
    )

    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discovered_hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    version: Mapped[TargetType] = mapped_column(
        Enum(TargetType, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
    )
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)
    network: Mapped[str | None] = mapped_column(String(64), nullable=True, doc="Subnet/CIDR, if knowable.")
    interface_name: Mapped[str | None] = mapped_column(
        String(64), nullable=True, doc="Never populated by a network-scan plugin; only an agent-based collector could know this."
    )

    host: Mapped["DiscoveredHost"] = relationship(back_populates="network_interfaces")
