"""Request/response schemas for the Host Inventory & Observation Engine.

Every resource here is read-only from the API's perspective — rows are only
ever written by :class:`backend.services.host_inventory_service.HostInventoryService`
as a side effect of a completed scan, never through a CRUD endpoint. Per
``.claude/CLAUDE.md``: purely descriptive, no severity/CVSS anywhere.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from backend.models.enums import (
    HostState,
    HostType,
    NetworkProtocol,
    ObservationCategory,
    PortState,
    TargetType,
    TechnologyCategory,
)


class NetworkInterfaceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    host_id: uuid.UUID
    ip_address: str
    version: TargetType
    mac_address: str | None
    network: str | None
    interface_name: str | None


class TechnologyRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    host_id: uuid.UUID
    service_id: uuid.UUID | None
    name: str
    vendor: str | None
    version: str | None
    category: TechnologyCategory
    first_seen: datetime
    last_seen: datetime


class OperatingSystemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    host_id: uuid.UUID
    vendor: str | None
    family: str | None
    name: str
    version: str | None
    accuracy: int
    source: str
    first_seen: datetime
    last_seen: datetime


class ServiceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    host_id: uuid.UUID
    port: int
    protocol: NetworkProtocol
    state: PortState
    service_name: str | None
    product: str | None
    vendor: str | None
    version: str | None
    extra_info: str | None
    banner: str | None
    first_seen: datetime
    last_seen: datetime


class ObservationEvidenceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    observation_id: uuid.UUID
    source_tool: str
    title: str | None
    content: str | None
    file_path: str | None
    created_at: datetime


class ObservationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    host_id: uuid.UUID | None
    service_id: uuid.UUID | None
    port: int | None
    plugin: str | None
    source: str
    category: ObservationCategory
    observation_type: str | None
    title: str
    detail: str | None
    first_seen: datetime
    last_seen: datetime
    evidence: list[ObservationEvidenceRead] = []


class ExecutionHistoryEntryRead(BaseModel):
    """One row of a host's (or observation's) execution history — who touched it, and when."""

    execution_id: uuid.UUID
    tool_name: str
    target_value: str
    is_new: bool
    created_at: datetime


class HostSummaryRead(BaseModel):
    """Lightweight shape for the Discovered Hosts list page — no nested collections."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    target_id: uuid.UUID | None
    assessment_id: uuid.UUID
    hostname: str | None
    fqdn: str | None
    ipv4: str | None
    ipv6: str | None
    mac_address: str | None
    host_type: HostType
    state: HostState
    first_seen: datetime
    last_seen: datetime
    service_count: int = 0


class HostDetailRead(BaseModel):
    """Full Discovered Host Details page shape: every nested collection."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    target_id: uuid.UUID | None
    assessment_id: uuid.UUID
    hostname: str | None
    fqdn: str | None
    ipv4: str | None
    ipv6: str | None
    mac_address: str | None
    mac_vendor: str | None
    host_type: HostType
    state: HostState
    fingerprint: str
    first_seen: datetime
    last_seen: datetime
    source_execution_id: uuid.UUID | None
    network_interfaces: list[NetworkInterfaceRead] = []
    services: list[ServiceRead] = []
    technologies: list[TechnologyRead] = []
    operating_systems: list[OperatingSystemRead] = []
    observations: list[ObservationRead] = []
    execution_history: list[ExecutionHistoryEntryRead] = []


class SearchResult(BaseModel):
    """One matched row in a global search, generic across resource kinds.

    ``assessment_id`` lets the frontend deep-link a result into the
    Assessment that discovered it (its "Assets Discovered" tab) rather
    than a dedicated per-resource page — inventory data is contextual to
    an assessment, not a standalone destination.
    """

    kind: str
    id: uuid.UUID
    host_id: uuid.UUID | None
    assessment_id: uuid.UUID | None
    label: str
    detail: str | None


class SearchResponse(BaseModel):
    query: str
    hosts: list[SearchResult] = []
    services: list[SearchResult] = []
    technologies: list[SearchResult] = []
    observations: list[SearchResult] = []
    findings: list[SearchResult] = []
