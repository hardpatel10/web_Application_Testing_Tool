"""Read-side service for the Correlation Engine's Findings API.

Distinct from :class:`backend.services.correlation_service.CorrelationService`
(the write-side rule-evaluation engine) — mirrors the same split Phase 8
established between :class:`~backend.services.host_inventory_service.HostInventoryService`
and :class:`~backend.services.host_inventory_query_service.HostInventoryQueryService`.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import InvalidInputError, NotFoundError
from backend.database.pagination import Page, Pagination, Sort, SortDirection
from backend.models.correlation_run import CorrelationRun
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import FindingConfidence, FindingSeverity, FindingStatus
from backend.models.execution_host import ExecutionHost
from backend.models.finding import Finding, FindingEvidence, FindingObservation, FindingReference
from backend.models.observation import Observation
from backend.models.service import Service
from backend.models.target import Target
from backend.models.tool import Tool
from backend.models.tool_execution import ToolExecution
from backend.schemas.host_inventory import ExecutionHistoryEntryRead, HostSummaryRead, ObservationRead, ServiceRead
from backend.schemas.finding import (
    CorrelationRunRead,
    CorrelationStatusRead,
    FindingDetailRead,
    FindingEvidenceRead,
    FindingReferenceRead,
    FindingSummaryRead,
)
from backend.services.query_scoping import owned_by_active_assessment

_FINDING_SORT_FIELDS = {"severity", "confidence", "first_seen", "last_seen", "created_at", "title", "status"}
_RECENT_RUNS_LIMIT = 10


class FindingQueryService:
    """Search/filter/sort/paginate reads across correlated findings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_findings(
        self,
        *,
        assessment_id: uuid.UUID | None = None,
        host_id: uuid.UUID | None = None,
        severity: FindingSeverity | None = None,
        confidence: FindingConfidence | None = None,
        status: FindingStatus | None = None,
        category: str | None = None,
        plugin: str | None = None,
        rule_id: str | None = None,
        search: str | None = None,
        sort: Sort | None = None,
        pagination: Pagination | None = None,
    ) -> Page[FindingSummaryRead]:
        pagination = pagination or Pagination()
        sort = sort or Sort(field="last_seen", direction=SortDirection.DESC)
        if sort.field not in _FINDING_SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort findings by '{sort.field}'.")

        conditions = [owned_by_active_assessment(Finding.assessment_id)]
        if assessment_id is not None:
            conditions.append(Finding.assessment_id == assessment_id)
        if host_id is not None:
            conditions.append(Finding.host_id == host_id)
        if severity is not None:
            conditions.append(Finding.severity == severity)
        if confidence is not None:
            conditions.append(Finding.confidence == confidence)
        if status is not None:
            conditions.append(Finding.status == status)
        if category is not None:
            conditions.append(Finding.category == category)
        if plugin is not None:
            conditions.append(Finding.plugin == plugin)
        if rule_id is not None:
            conditions.append(Finding.rule_id == rule_id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append((Finding.title.ilike(term)) | (Finding.description.ilike(term)))

        sort_column = getattr(Finding, sort.field)
        order_by = sort_column.desc() if sort.direction == SortDirection.DESC else sort_column.asc()

        total = (await self._session.execute(select(func.count()).select_from(Finding).where(*conditions))).scalar_one()
        stmt = select(Finding).where(*conditions).order_by(order_by).offset(pagination.offset).limit(pagination.page_size)
        findings = list((await self._session.execute(stmt)).scalars().all())

        host_labels: dict[uuid.UUID, str] = {}
        host_ids = [f.host_id for f in findings if f.host_id is not None]
        if host_ids:
            host_rows = (
                await self._session.execute(select(DiscoveredHost).where(DiscoveredHost.id.in_(host_ids)))
            ).scalars().all()
            for host in host_rows:
                host_labels[host.id] = host.hostname or host.ipv4 or host.ipv6 or str(host.id)

        evidence_counts: dict[uuid.UUID, int] = {}
        observation_counts: dict[uuid.UUID, int] = {}
        finding_ids = [f.id for f in findings]
        if finding_ids:
            evidence_rows = (
                await self._session.execute(
                    select(FindingEvidence.finding_id, func.count(FindingEvidence.id))
                    .where(FindingEvidence.finding_id.in_(finding_ids))
                    .group_by(FindingEvidence.finding_id)
                )
            ).all()
            evidence_counts = dict(evidence_rows)
            observation_rows = (
                await self._session.execute(
                    select(FindingObservation.finding_id, func.count(FindingObservation.id))
                    .where(FindingObservation.finding_id.in_(finding_ids))
                    .group_by(FindingObservation.finding_id)
                )
            ).all()
            observation_counts = dict(observation_rows)

        items = []
        for finding in findings:
            summary = FindingSummaryRead.model_validate(finding)
            summary.host_label = host_labels.get(finding.host_id) if finding.host_id else None
            summary.evidence_count = evidence_counts.get(finding.id, 0)
            summary.observation_count = observation_counts.get(finding.id, 0)
            items.append(summary)
        return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    async def get_finding(self, finding_id: uuid.UUID) -> FindingDetailRead:
        stmt = (
            select(Finding)
            .options(
                selectinload(Finding.evidence),
                selectinload(Finding.references),
                selectinload(Finding.observation_links).selectinload(FindingObservation.observation),
                selectinload(Finding.host),
            )
            .where(Finding.id == finding_id, owned_by_active_assessment(Finding.assessment_id))
        )
        finding = (await self._session.execute(stmt)).scalar_one_or_none()
        if finding is None:
            raise NotFoundError(f"Finding {finding_id} not found.")

        detail = FindingDetailRead.model_validate(finding)
        detail.evidence = [FindingEvidenceRead.model_validate(e) for e in finding.evidence]
        detail.references = [FindingReferenceRead.model_validate(r) for r in finding.references]
        detail.supporting_observations = [
            ObservationRead.model_validate(link.observation) for link in finding.observation_links
        ]

        if finding.host_id is not None:
            host = await self._session.get(DiscoveredHost, finding.host_id)
            if host is not None:
                detail.host = HostSummaryRead.model_validate(host)
                services = (
                    await self._session.execute(select(Service).where(Service.host_id == host.id))
                ).scalars().all()
                detail.affected_services = [ServiceRead.model_validate(s) for s in services]

                history_stmt = (
                    select(ExecutionHost, Tool, Target)
                    .join(ToolExecution, ToolExecution.id == ExecutionHost.execution_id)
                    .join(Tool, Tool.id == ToolExecution.tool_id)
                    .join(Target, Target.id == ToolExecution.target_id)
                    .where(ExecutionHost.host_id == host.id)
                    .order_by(ExecutionHost.created_at.desc())
                )
                history_rows = (await self._session.execute(history_stmt)).all()
                detail.execution_history = [
                    ExecutionHistoryEntryRead(
                        execution_id=link.execution_id, tool_name=tool.name,
                        target_value=target.target_value,
                        is_new=link.is_new, created_at=link.created_at,
                    )
                    for link, tool, target in history_rows
                ]

        return detail

    # -- Correlation status -------------------------------------------------

    async def correlation_status(self, registered_rule_count: int) -> CorrelationStatusRead:
        stmt = (
            select(CorrelationRun)
            .where(CorrelationRun.assessment_id.is_(None) | owned_by_active_assessment(CorrelationRun.assessment_id))
            .order_by(CorrelationRun.started_at.desc())
            .limit(_RECENT_RUNS_LIMIT)
        )
        runs = list((await self._session.execute(stmt)).scalars().all())
        recent = [CorrelationRunRead.model_validate(run) for run in runs]
        return CorrelationStatusRead(
            registered_rule_count=registered_rule_count,
            last_run=recent[0] if recent else None,
            recent_runs=recent,
        )
