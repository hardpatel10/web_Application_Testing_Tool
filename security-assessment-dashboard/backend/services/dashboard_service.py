"""The Intelligence Dashboard's aggregation layer.

Every method here is a ``GROUP BY``/``COUNT``/``AVG`` aggregated query against
the real tables Phase 6-9 already populate -- never a Python-side loop over
every row (the phase brief's "avoid N+1 queries" / "support future datasets
with thousands of hosts" performance requirement). Read-only, like
:class:`backend.services.host_inventory_query_service.HostInventoryQueryService`
and :class:`backend.services.finding_query_service.FindingQueryService`.

Every aggregation optionally scopes to one ``assessment_id``; omitted, it
reports across the whole workspace (every assessment), matching how the
existing Dashboard page already frames itself as a workspace-wide view.

Per the corrected domain model (Assessment -> Target -> Execution ->
DiscoveredHost), the overview reports both ``targets`` (the user-supplied
assessment scope) and ``hosts_discovered`` (what scans found within it) as
separate, equally first-class counts -- not just "assets," which used to
read as if the discovered hosts *were* the assessment's scope.
"""

import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.assessment import Assessment
from backend.models.base import utcnow
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import FindingSeverity, FindingStatus, ToolExecutionStatus
from backend.models.finding import Finding
from backend.models.observation import Observation
from backend.models.operating_system import OperatingSystem
from backend.models.report import Report
from backend.models.service import Service
from backend.models.target import Target
from backend.models.technology import Technology
from backend.models.tool_execution import ToolExecution
from backend.schemas.dashboard import (
    ChartSeries,
    CountItem,
    DashboardRead,
    ExecutionSummary,
    FindingDashboard,
    HostDashboard,
    HostSummaryStats,
    OverviewStats,
    SeverityCounts,
    StatisticsRead,
    TrendPoint,
)
from backend.schemas.finding import FindingSummaryRead
from backend.schemas.host_inventory import HostSummaryRead
from backend.services.query_scoping import owned_by_active_assessment

_TOP_N = 10
_TREND_DAYS = 30
_RESOLVED_STATUSES = (FindingStatus.REMEDIATED, FindingStatus.FALSE_POSITIVE, FindingStatus.ACCEPTED_RISK, FindingStatus.DUPLICATE)


class DashboardService:
    """Assembles the Intelligence Dashboard's overview, summaries, charts, and top lists."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_dashboard(self, assessment_id: uuid.UUID | None = None) -> DashboardRead:
        overview = await self._overview(assessment_id)
        security_summary = await self._security_summary(assessment_id)
        execution_summary = await self._execution_summary(assessment_id)
        host_summary = await self._host_summary(assessment_id)
        finding_dashboard = await self._finding_dashboard(assessment_id)
        host_dashboard = await self._host_dashboard(assessment_id)
        charts = await self._charts(assessment_id)

        is_empty = overview.hosts_discovered == 0 and overview.findings == 0 and overview.observations == 0

        return DashboardRead(
            is_empty=is_empty, overview=overview, security_summary=security_summary,
            execution_summary=execution_summary, host_summary=host_summary,
            finding_dashboard=finding_dashboard, host_dashboard=host_dashboard, charts=charts,
        )

    async def get_statistics(self, assessment_id: uuid.UUID | None = None) -> StatisticsRead:
        return StatisticsRead(
            overview=await self._overview(assessment_id),
            security_summary=await self._security_summary(assessment_id),
            execution_summary=await self._execution_summary(assessment_id),
        )

    # -- Overview / summaries -------------------------------------------------

    async def _overview(self, assessment_id: uuid.UUID | None) -> OverviewStats:
        assessment_count = await self._count(Assessment, self._scope(Assessment.id, assessment_id))
        return OverviewStats(
            assessments=assessment_count,
            targets=await self._count(Target, self._scope(Target.assessment_id, assessment_id)),
            hosts_discovered=await self._count(DiscoveredHost, self._scope(DiscoveredHost.assessment_id, assessment_id)),
            services=await self._count_joined_to_host(Service, assessment_id),
            technologies=await self._count_joined_to_host(Technology, assessment_id),
            observations=await self._count_joined_to_host(Observation, assessment_id),
            findings=await self._count(Finding, self._scope(Finding.assessment_id, assessment_id)),
            reports=await self._count(Report, self._scope(Report.assessment_id, assessment_id)),
        )

    async def _security_summary(self, assessment_id: uuid.UUID | None) -> SeverityCounts:
        conditions = self._scope(Finding.assessment_id, assessment_id)
        stmt = select(Finding.severity, func.count(Finding.id)).where(*conditions).group_by(Finding.severity)
        rows = dict((await self._session.execute(stmt)).all())
        return SeverityCounts(
            critical=rows.get(FindingSeverity.CRITICAL, 0),
            high=rows.get(FindingSeverity.HIGH, 0),
            medium=rows.get(FindingSeverity.MEDIUM, 0),
            low=rows.get(FindingSeverity.LOW, 0),
            info=rows.get(FindingSeverity.INFO, 0),
        )

    async def _execution_summary(self, assessment_id: uuid.UUID | None) -> ExecutionSummary:
        conditions = self._scope(ToolExecution.assessment_id, assessment_id)
        stmt = select(ToolExecution.status, func.count(ToolExecution.id)).where(*conditions).group_by(ToolExecution.status)
        rows = dict((await self._session.execute(stmt)).all())
        avg_stmt = select(func.avg(ToolExecution.duration)).where(*conditions, ToolExecution.duration.is_not(None))
        average_duration = (await self._session.execute(avg_stmt)).scalar_one()
        return ExecutionSummary(
            completed=rows.get(ToolExecutionStatus.COMPLETED, 0),
            running=rows.get(ToolExecutionStatus.RUNNING, 0),
            failed=rows.get(ToolExecutionStatus.FAILED, 0) + rows.get(ToolExecutionStatus.TIMEOUT, 0),
            cancelled=rows.get(ToolExecutionStatus.CANCELLED, 0),
            average_duration_seconds=round(average_duration, 2) if average_duration is not None else None,
        )

    async def _host_summary(self, assessment_id: uuid.UUID | None) -> HostSummaryStats:
        return HostSummaryStats(
            hosts=await self._count(DiscoveredHost, self._scope(DiscoveredHost.assessment_id, assessment_id)),
            operating_systems=await self._count_joined_to_host(OperatingSystem, assessment_id),
            technologies=await self._count_joined_to_host(Technology, assessment_id),
            services=await self._count_joined_to_host(Service, assessment_id),
            top_open_ports=await self._top_ports(assessment_id),
            top_technologies=await self._top_technologies(assessment_id),
        )

    # -- Finding dashboard ------------------------------------------------------

    async def _finding_dashboard(self, assessment_id: uuid.UUID | None) -> FindingDashboard:
        conditions = self._scope(Finding.assessment_id, assessment_id)

        by_severity = await self._group_count(Finding.severity, conditions, value_fn=lambda v: v.value)
        by_category = await self._group_count(Finding.category, conditions, value_fn=lambda v: v or "uncategorized")
        by_plugin = await self._group_count(Finding.plugin, conditions, value_fn=lambda v: v or "unknown")

        host_rows = (
            await self._session.execute(
                select(Finding.host_id, func.count(Finding.id))
                .where(*conditions, Finding.host_id.is_not(None))
                .group_by(Finding.host_id)
                .order_by(func.count(Finding.id).desc())
                .limit(_TOP_N)
            )
        ).all()
        by_host: list[CountItem] = []
        if host_rows:
            host_ids = [row[0] for row in host_rows]
            hosts = (await self._session.execute(select(DiscoveredHost).where(DiscoveredHost.id.in_(host_ids)))).scalars().all()
            raw_labels = {host.id: host.hostname or host.ipv4 or host.ipv6 or str(host.id) for host in hosts}
            labels = self._disambiguate(raw_labels)
            by_host = [CountItem(label=labels.get(host_id, str(host_id)), count=count) for host_id, count in host_rows]

        newest_stmt = select(Finding).where(*conditions).order_by(Finding.first_seen.desc()).limit(_TOP_N)
        newest_findings = (await self._session.execute(newest_stmt)).scalars().all()

        open_count = await self._count(Finding, [*conditions, Finding.status.in_((FindingStatus.OPEN, FindingStatus.CONFIRMED))])
        resolved_count = await self._count(Finding, [*conditions, Finding.status.in_(_RESOLVED_STATUSES)])

        return FindingDashboard(
            by_severity=by_severity, by_category=by_category, by_plugin=by_plugin, by_host=by_host,
            newest=[FindingSummaryRead.model_validate(f) for f in newest_findings],
            open_count=open_count, resolved_count=resolved_count,
        )

    # -- Host dashboard ----------------------------------------------------

    async def _host_dashboard(self, assessment_id: uuid.UUID | None) -> HostDashboard:
        conditions = self._scope(DiscoveredHost.assessment_id, assessment_id)

        newest_stmt = select(DiscoveredHost).where(*conditions).order_by(DiscoveredHost.first_seen.desc()).limit(_TOP_N)
        newest_hosts = (await self._session.execute(newest_stmt)).scalars().all()

        most_active_stmt = (
            select(DiscoveredHost.id, DiscoveredHost.hostname, DiscoveredHost.ipv4, DiscoveredHost.ipv6, func.count(Service.id))
            .join(Service, Service.host_id == DiscoveredHost.id)
            .where(*conditions)
            .group_by(DiscoveredHost.id)
            .order_by(func.count(Service.id).desc())
            .limit(_TOP_N)
        )
        most_active_rows = (await self._session.execute(most_active_stmt)).all()
        most_active_labels = self._disambiguate(
            {host_id: hostname or ipv4 or ipv6 or str(host_id) for host_id, hostname, ipv4, ipv6, _count in most_active_rows}
        )
        most_active = [
            CountItem(label=most_active_labels[host_id], count=count) for host_id, _hostname, _ipv4, _ipv6, count in most_active_rows
        ]

        os_conditions = self._scope(DiscoveredHost.assessment_id, assessment_id)
        os_stmt = (
            select(OperatingSystem.name, func.count(OperatingSystem.id))
            .join(DiscoveredHost, DiscoveredHost.id == OperatingSystem.host_id)
            .where(*os_conditions)
            .group_by(OperatingSystem.name)
            .order_by(func.count(OperatingSystem.id).desc())
            .limit(_TOP_N)
        )
        operating_systems = [CountItem(label=name, count=count) for name, count in (await self._session.execute(os_stmt)).all()]

        return HostDashboard(
            newest=[HostSummaryRead.model_validate(h) for h in newest_hosts],
            most_active=most_active,
            operating_systems=operating_systems,
            technology_distribution=await self._top_technologies(assessment_id),
            service_distribution=await self._service_distribution(assessment_id),
        )

    # -- Charts ---------------------------------------------------------------

    async def _charts(self, assessment_id: uuid.UUID | None) -> ChartSeries:
        since = utcnow() - timedelta(days=_TREND_DAYS)
        return ChartSeries(
            execution_timeline=await self._trend(ToolExecution.created_at, self._scope(ToolExecution.assessment_id, assessment_id), since),
            observation_trend=await self._trend(Observation.first_seen, self._scope_via_host(Observation, assessment_id), since),
            finding_trend=await self._trend(Finding.first_seen, self._scope(Finding.assessment_id, assessment_id), since),
            host_growth=await self._trend(DiscoveredHost.first_seen, self._scope(DiscoveredHost.assessment_id, assessment_id), since),
        )

    async def _trend(self, date_column, conditions: list, since) -> list[TrendPoint]:
        stmt = (
            select(func.date(date_column), func.count())
            .where(*conditions, date_column >= since)
            .group_by(func.date(date_column))
            .order_by(func.date(date_column))
        )
        rows = (await self._session.execute(stmt)).all()
        return [TrendPoint(date=str(date), count=count) for date, count in rows if date is not None]

    # -- Shared helpers -------------------------------------------------------

    @staticmethod
    def _scope(column, assessment_id: uuid.UUID | None) -> list:
        """Restrict ``column`` (an ``assessment_id`` FK) to a live, non-soft-deleted assessment.

        Always excludes soft-deleted assessments' rows -- not just when
        ``assessment_id`` narrows to one -- so the unscoped, workspace-wide
        dashboard never counts a deleted assessment's leftover data either.
        """
        conditions = [owned_by_active_assessment(column)]
        if assessment_id is not None:
            conditions.append(column == assessment_id)
        return conditions

    @staticmethod
    def _disambiguate(labels: dict[uuid.UUID, str]) -> dict[uuid.UUID, str]:
        """Append a short id suffix to any label shared by more than one host.

        Host identity is scoped per-target (post-refactor), and a target's
        fingerprint scope per-assessment before that -- either way, the same
        hostname (e.g. "localhost") legitimately recurs across separate
        targets/assessments -- collapsing them to one indistinguishable chart
        label would both mislead the reader and violate distinct-identity
        (duplicate axis/key) assumptions the chart layer relies on.
        """
        seen: dict[str, int] = {}
        for label in labels.values():
            seen[label] = seen.get(label, 0) + 1
        return {
            host_id: f"{label} ({str(host_id)[:8]})" if seen[label] > 1 else label
            for host_id, label in labels.items()
        }

    def _scope_via_host(self, model, assessment_id: uuid.UUID | None) -> list:
        host_conditions = self._scope(DiscoveredHost.assessment_id, assessment_id)
        return [model.host_id.in_(select(DiscoveredHost.id).where(*host_conditions))]

    async def _count(self, model, conditions: list) -> int:
        stmt = select(func.count()).select_from(model).where(*conditions)
        return (await self._session.execute(stmt)).scalar_one()

    async def _count_joined_to_host(self, model, assessment_id: uuid.UUID | None) -> int:
        """Count rows of a model with a ``host_id`` FK, scoped to an assessment via a join to DiscoveredHost."""
        stmt = select(func.count()).select_from(model).join(DiscoveredHost, DiscoveredHost.id == model.host_id)
        conditions = self._scope(DiscoveredHost.assessment_id, assessment_id)
        if conditions:
            stmt = stmt.where(*conditions)
        return (await self._session.execute(stmt)).scalar_one()

    async def _group_count(self, column, conditions: list, *, value_fn) -> list[CountItem]:
        stmt = (
            select(column, func.count())
            .where(*conditions)
            .group_by(column)
            .order_by(func.count().desc())
            .limit(_TOP_N)
        )
        rows = (await self._session.execute(stmt)).all()
        return [CountItem(label=value_fn(value), count=count) for value, count in rows]

    async def _top_ports(self, assessment_id: uuid.UUID | None) -> list[CountItem]:
        from backend.models.enums import PortState

        stmt = (
            select(Service.port, func.count(Service.id))
            .join(DiscoveredHost, DiscoveredHost.id == Service.host_id)
            .where(Service.state == PortState.OPEN, *self._scope(DiscoveredHost.assessment_id, assessment_id))
            .group_by(Service.port)
            .order_by(func.count(Service.id).desc())
            .limit(_TOP_N)
        )
        rows = (await self._session.execute(stmt)).all()
        return [CountItem(label=str(port), count=count) for port, count in rows]

    async def _top_technologies(self, assessment_id: uuid.UUID | None) -> list[CountItem]:
        stmt = (
            select(Technology.name, func.count(Technology.id))
            .join(DiscoveredHost, DiscoveredHost.id == Technology.host_id)
            .where(*self._scope(DiscoveredHost.assessment_id, assessment_id))
            .group_by(Technology.name)
            .order_by(func.count(Technology.id).desc())
            .limit(_TOP_N)
        )
        rows = (await self._session.execute(stmt)).all()
        return [CountItem(label=name, count=count) for name, count in rows]

    async def _service_distribution(self, assessment_id: uuid.UUID | None) -> list[CountItem]:
        from backend.models.enums import PortState

        stmt = (
            select(Service.service_name, func.count(Service.id))
            .join(DiscoveredHost, DiscoveredHost.id == Service.host_id)
            .where(Service.state == PortState.OPEN, Service.service_name.is_not(None), *self._scope(DiscoveredHost.assessment_id, assessment_id))
            .group_by(Service.service_name)
            .order_by(func.count(Service.id).desc())
            .limit(_TOP_N)
        )
        rows = (await self._session.execute(stmt)).all()
        return [CountItem(label=name, count=count) for name, count in rows]
