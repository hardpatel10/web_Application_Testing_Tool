"""The common shape a scanner plugin's ``normalize()`` returns.

Nmap (Phase 7) is the reference implementation, but this shape is
deliberately generic and tool-agnostic — any future scanner plugin
(naabu discovering ports, httpx fingerprinting web services, ...) returns
the same two lists from its own ``normalize()``, so
:class:`~backend.services.host_inventory_service.HostInventoryService`
has exactly one shape to translate into durable ``DiscoveredHost``/``Service``/
``Technology``/``OperatingSystem``/``Observation`` rows, regardless of
which tool produced it.

Per ``.claude/CLAUDE.md`` and this phase's explicit instruction, none of
these carry a severity, CVSS score, or any vulnerability judgment — that
remains ``Finding``'s job, for a future correlation phase. A plugin
without a profile/normalization system (the 15 detection-only tools, the
``dummy-execution`` test fixture) is unaffected: it simply doesn't return
this type, and the engine's ``isinstance`` check skips structured
persistence for it.

``NormalizedHost`` carries *every* address and *every* OS candidate a
plugin reports (``addresses``/``os_matches``, both lists) rather than only
a single "best" value — Phase 7's version kept only the first IPv4/IPv6
address and the single highest-accuracy OS match, silently discarding the
rest; Phase 8's persistence layer needs the full picture to populate
``NetworkInterface``/``OperatingSystem`` without data loss.
"""

from pydantic import BaseModel

from backend.models.enums import HostState, NetworkProtocol, PortState, TargetType


class NormalizedService(BaseModel):
    """One port/protocol observed on a host — maps directly onto a ``Service`` row."""

    port: int
    protocol: NetworkProtocol
    state: PortState
    service_name: str | None = None
    product: str | None = None
    version: str | None = None
    extra_info: str | None = None
    banner: str | None = None


class NormalizedObservation(BaseModel):
    """One neutral, descriptive fact — maps directly onto an ``Observation`` row.

    ``host_index``/``port`` associate the observation back to one of
    ``NormalizedOutput.hosts`` (by list position) and, optionally, one of
    that host's ports — resolved to real foreign keys only once the
    engine persists these against real ``DiscoveredHost`` rows.
    """

    source: str
    title: str
    detail: str | None = None
    host_index: int | None = None
    port: int | None = None
    category: str = "other"
    observation_type: str | None = None


class NormalizedAddress(BaseModel):
    """One address a plugin reported for a host — maps onto a ``NetworkInterface`` row."""

    ip_address: str
    version: TargetType
    mac_address: str | None = None


class NormalizedOsMatch(BaseModel):
    """One OS candidate a plugin reported for a host — maps onto an ``OperatingSystem`` row."""

    name: str
    accuracy: int
    vendor: str | None = None
    family: str | None = None


class NormalizedHost(BaseModel):
    """One discovered host — maps onto a ``DiscoveredHost`` row plus its child rows."""

    hostname: str | None = None
    fqdn: str | None = None
    addresses: list[NormalizedAddress] = []
    mac_address: str | None = None
    mac_vendor: str | None = None
    state: HostState = HostState.UNKNOWN
    os_matches: list[NormalizedOsMatch] = []
    services: list[NormalizedService] = []


class NormalizedOutput(BaseModel):
    """A scanner plugin's fully normalized result: hosts and observations only."""

    hosts: list[NormalizedHost] = []
    observations: list[NormalizedObservation] = []
