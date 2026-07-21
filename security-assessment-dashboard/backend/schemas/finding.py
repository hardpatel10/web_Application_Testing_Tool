"""Request/response schemas for the Correlation Engine's Findings API.

Every resource here is read-only from the API's perspective, except
triggering a correlation run itself — findings are only ever written by
:class:`backend.services.correlation_service.CorrelationService`.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, FindingStatus
from backend.schemas.host_inventory import ExecutionHistoryEntryRead, HostSummaryRead, ObservationRead, ServiceRead


class FindingReferenceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    reference_type: FindingReferenceType
    reference_value: str


class FindingEvidenceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    source_tool: str
    title: str | None
    content: str | None
    file_path: str | None
    created_at: datetime


class FindingSummaryRead(BaseModel):
    """Lightweight shape for the Findings list page."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    assessment_id: uuid.UUID
    host_id: uuid.UUID | None
    rule_id: str
    plugin: str | None
    title: str
    severity: FindingSeverity
    confidence: FindingConfidence
    category: str | None
    status: FindingStatus
    first_seen: datetime
    last_seen: datetime
    host_label: str | None = None
    evidence_count: int = 0
    observation_count: int = 0


class FindingDetailRead(BaseModel):
    """Full Finding Details page shape."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    assessment_id: uuid.UUID
    host_id: uuid.UUID | None
    source_execution_id: uuid.UUID | None
    rule_id: str
    plugin: str | None
    title: str
    description: str | None
    impact: str | None
    severity: FindingSeverity
    confidence: FindingConfidence
    category: str | None
    cvss_score: float | None
    cwe: str | None
    owasp: str | None
    remediation: str | None
    status: FindingStatus
    first_seen: datetime
    last_seen: datetime
    created_at: datetime
    updated_at: datetime
    host: HostSummaryRead | None = None
    affected_services: list[ServiceRead] = []
    supporting_observations: list[ObservationRead] = []
    evidence: list[FindingEvidenceRead] = []
    references: list[FindingReferenceRead] = []
    execution_history: list[ExecutionHistoryEntryRead] = []


class CorrelationRunRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    assessment_id: uuid.UUID | None
    status: str
    started_at: datetime
    completed_at: datetime | None
    hosts_evaluated: int
    rules_evaluated: int
    findings_created: int
    findings_updated: int
    error_message: str | None


class CorrelationRunRequest(BaseModel):
    assessment_id: uuid.UUID | None = None


class CorrelationRunResultRead(BaseModel):
    """Result of a just-completed correlation run -- real counts, not an estimate."""

    assessment_id: uuid.UUID | None
    hosts_evaluated: int
    rules_evaluated: int
    rule_count: int
    findings_created: int
    findings_updated: int


class CorrelationStatusRead(BaseModel):
    """The most recent correlation run's outcome, plus how many rules are registered."""

    registered_rule_count: int
    last_run: CorrelationRunRead | None
    recent_runs: list[CorrelationRunRead] = []
