"""Request/response schemas for a job's normalized scan results.

Generic and tool-agnostic, like the ``DiscoveredHost``/``Service``/``Observation``
models they read from — not Nmap-specific, even though Nmap (Phase 7) is
the only tool that currently populates them.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from backend.models.enums import HostState, NetworkProtocol, PortState, RawOutputFormat


class ServiceRead(BaseModel):
    id: uuid.UUID
    port: int
    protocol: NetworkProtocol
    state: PortState
    service_name: str | None
    product: str | None
    version: str | None
    extra_info: str | None


class HostRead(BaseModel):
    id: uuid.UUID
    ip_address: str | None
    hostname: str | None
    mac_address: str | None
    mac_vendor: str | None
    state: HostState
    os_name: str | None
    os_accuracy: int | None
    services: list[ServiceRead]


class ObservationRead(BaseModel):
    id: uuid.UUID
    host_id: uuid.UUID | None
    port: int | None
    source: str
    title: str
    detail: str | None


class JobResultsResponse(BaseModel):
    """One job's fully normalized results."""

    job_id: uuid.UUID
    hosts: list[HostRead]
    observations: list[ObservationRead]


class RawOutputResponse(BaseModel):
    """One job's raw, unmodified tool output."""

    job_id: uuid.UUID
    format: RawOutputFormat
    content: str | None
    created_at: datetime
