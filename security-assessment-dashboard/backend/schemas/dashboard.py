"""Request/response schemas for the Intelligence Dashboard's aggregation API.

Every number here comes from a real aggregated database query in
:class:`backend.services.dashboard_service.DashboardService` -- per
``.claude/CLAUDE.md``, nothing is estimated, randomized, or hardcoded as a
placeholder. An empty workspace produces zeroed counts and empty lists, not
fabricated sample data; the frontend is responsible for a professional empty
state when ``DashboardRead.is_empty`` is ``True``.
"""

from pydantic import BaseModel

from backend.schemas.finding import FindingSummaryRead
from backend.schemas.host_inventory import HostSummaryRead


class OverviewStats(BaseModel):
    """The workspace's top-line counts -- ``targets`` is the user-supplied assessment scope, ``hosts_discovered`` is what scans found within it."""

    assessments: int
    targets: int
    hosts_discovered: int
    services: int
    technologies: int
    observations: int
    findings: int
    reports: int


class SeverityCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class ExecutionSummary(BaseModel):
    completed: int = 0
    running: int = 0
    failed: int = 0
    cancelled: int = 0
    average_duration_seconds: float | None = None


class CountItem(BaseModel):
    label: str
    count: int


class TrendPoint(BaseModel):
    date: str
    count: int


class HostSummaryStats(BaseModel):
    hosts: int
    operating_systems: int
    technologies: int
    services: int
    top_open_ports: list[CountItem] = []
    top_technologies: list[CountItem] = []


class FindingDashboard(BaseModel):
    by_severity: list[CountItem] = []
    by_category: list[CountItem] = []
    by_plugin: list[CountItem] = []
    by_host: list[CountItem] = []
    newest: list[FindingSummaryRead] = []
    open_count: int = 0
    resolved_count: int = 0


class HostDashboard(BaseModel):
    newest: list[HostSummaryRead] = []
    most_active: list[CountItem] = []
    operating_systems: list[CountItem] = []
    technology_distribution: list[CountItem] = []
    service_distribution: list[CountItem] = []


class ChartSeries(BaseModel):
    execution_timeline: list[TrendPoint] = []
    observation_trend: list[TrendPoint] = []
    finding_trend: list[TrendPoint] = []
    host_growth: list[TrendPoint] = []


class DashboardRead(BaseModel):
    is_empty: bool
    overview: OverviewStats
    security_summary: SeverityCounts
    execution_summary: ExecutionSummary
    host_summary: HostSummaryStats
    finding_dashboard: FindingDashboard
    host_dashboard: HostDashboard
    charts: ChartSeries


class StatisticsRead(BaseModel):
    """A lighter-weight numbers-only subset of the dashboard, for ``GET /statistics``."""

    overview: OverviewStats
    security_summary: SeverityCounts
    execution_summary: ExecutionSummary
