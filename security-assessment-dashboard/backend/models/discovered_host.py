"""The ``DiscoveredHost`` model: one durable host/website/API/domain discovered under a ``Target``.

Generic and tool-agnostic — not an Nmap-specific table. A ``DiscoveredHost``
is a child of the ``Target`` that discovered it, not a top-level sibling of
``Target`` under ``Assessment``: the assessment's real scope is whatever
targets the user supplied (``backend.models.target``), and everything a scan
turns up (hosts, services, technologies, observations) hangs off that target.
Identity is scoped per-target (mirrors ``Target``'s own
``uq_targets_assessment_id_target_value`` pattern): the same IP discovered
under two different targets in the same assessment (e.g. added once as its
own target, and again swept as part of a CIDR range) is two separate
``DiscoveredHost`` rows, since a host's identity here is "what this target's
scans found," not a workspace-wide inventory key.

``assessment_id`` is denormalized onto this table in addition to ``target_id``
(same precedent as ``backend.models.tool_execution.ToolExecution``, which
carries both ``assessment_id`` and ``target_id`` for the same reason) so
hosts can be queried/cascade-scoped per-assessment without a join through
``targets``.

A ``DiscoveredHost`` is not tied 1:1 to a single ``ToolExecution`` — it is
deduplicated across repeated scans of the same target via ``fingerprint``
(see ``backend.services.fingerprinting``), with ``first_seen``/``last_seen``
tracking its lifecycle and ``ExecutionHost`` recording every execution that
ever touched it (see ``backend.models.execution_host``).
``source_execution_id`` is only "the execution that first discovered this" —
a convenience pointer, not the source of truth for history.

Per ``.claude/CLAUDE.md``, this stores observed facts only: no severity, no
CVSS, no vulnerability judgment of any kind — that remains ``Finding``'s job
(``backend.models.finding``).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import HostState, HostType

if TYPE_CHECKING:
    from backend.models.assessment import Assessment
    from backend.models.execution_host import ExecutionHost
    from backend.models.finding import Finding
    from backend.models.network_interface import NetworkInterface
    from backend.models.observation import Observation
    from backend.models.operating_system import OperatingSystem
    from backend.models.service import Service
    from backend.models.target import Target
    from backend.models.technology import Technology
    from backend.models.tool_execution import ToolExecution


class DiscoveredHost(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One durable host/website/API/domain, deduplicated across scans of the same target."""

    __tablename__ = "discovered_hosts"
    __table_args__ = (
        Index("uq_discovered_hosts_target_id_fingerprint", "target_id", "fingerprint", unique=True),
    )

    #: The Assessment Target that discovered this host (its structural parent).
    #: Nullable only for legacy rows migrated from before this column existed,
    #: whose execution/target history could not be resolved (see the
    #: rename-and-backfill migration) — never fabricated. Every row created
    #: by the application going forward always sets this.
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fqdn: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ipv4: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)
    ipv6: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)
    mac_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    host_type: Mapped[HostType] = mapped_column(
        Enum(HostType, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        default=HostType.HOST,
    )
    state: Mapped[HostState] = mapped_column(
        Enum(HostState, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        default=HostState.UNKNOWN,
    )
    #: Deterministic merge key from ``backend.services.fingerprinting.host_fingerprint`` —
    #: the mechanism that decides "have I seen this host before" (see the unique index above).
    fingerprint: Mapped[str] = mapped_column(String(80), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    target: Mapped["Target | None"] = relationship(back_populates="discovered_hosts")
    assessment: Mapped["Assessment"] = relationship(back_populates="discovered_hosts")
    source_execution: Mapped["ToolExecution | None"] = relationship(foreign_keys=[source_execution_id])
    network_interfaces: Mapped[list["NetworkInterface"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", passive_deletes=True
    )
    services: Mapped[list["Service"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", passive_deletes=True
    )
    technologies: Mapped[list["Technology"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", passive_deletes=True
    )
    operating_systems: Mapped[list["OperatingSystem"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", passive_deletes=True
    )
    observations: Mapped[list["Observation"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", passive_deletes=True
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", passive_deletes=True
    )
    execution_links: Mapped[list["ExecutionHost"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", passive_deletes=True
    )
