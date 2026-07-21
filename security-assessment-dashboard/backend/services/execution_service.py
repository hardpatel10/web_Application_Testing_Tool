"""Service layer for the Assessment Execution Engine.

Bridges the API layer with :mod:`backend.workers` (planning, queuing,
dispatch -- see that package's docstring) and the database (a
``ToolExecution`` row *is* a job; there is no separate "Job" table).
Translates :mod:`backend.workers.exceptions` into
:mod:`backend.core.exceptions` at this boundary, the same
translate-at-the-service-boundary pattern ``PluginService``/``ToolService``
already use for the plugin framework.
"""

import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.exceptions import ConflictError, InvalidInputError, NotFoundError
from backend.models.assessment import Assessment
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import ToolExecutionStatus
from backend.models.execution_host import ExecutionHost
from backend.models.observation import Observation
from backend.models.raw_tool_output import RawToolOutput
from backend.models.tool_execution import ToolExecution
from backend.plugins.manager.plugin_manager import PluginManager
from backend.schemas.execution import (
    AssessmentProgress,
    ExecuteRequest,
    ExecuteResponse,
    JobLogsResponse,
    JobRead,
)
from backend.schemas.scan_result import HostRead, JobResultsResponse, ObservationRead, RawOutputResponse, ServiceRead
from backend.services.query_scoping import owned_by_active_assessment
from backend.workers.exceptions import JobNotCancellableError, JobNotFoundError, JobNotRetriableError
from backend.workers.logger import ExecutionLogger
from backend.workers.manager import ExecutionManager
from backend.workers.planner import ExecutionPlanner, ToolExecutionOptions

_SORT_FIELDS = {"created_at", "started_at", "completed_at", "status"}


class ExecutionService:
    """Business logic for planning, queuing, monitoring, cancelling, and retrying jobs."""

    def __init__(self, session: AsyncSession, plugin_manager: PluginManager, manager: ExecutionManager) -> None:
        self._session = session
        self._plugins = plugin_manager
        self._manager = manager

    # -- Commands -----------------------------------------------------------

    async def execute_assessment(self, assessment_id: uuid.UUID, payload: ExecuteRequest) -> ExecuteResponse:
        """Plan jobs for the requested tools/targets, then queue every runnable one."""
        await self._get_assessment_or_404(assessment_id)

        tool_options = (
            {name: ToolExecutionOptions(options.profile_id, options.advanced_options) for name, options in payload.tool_options.items()}
            if payload.tool_options
            else None
        )
        planner = ExecutionPlanner(self._session, self._plugins)
        jobs = await planner.plan(assessment_id, payload.tool_names, payload.target_ids, tool_options)

        # ExecutionManager.enqueue() reads/writes these rows through its own
        # backend.database.session.background_session() (a separate
        # connection/transaction from this request-scoped session, since job
        # execution outlives the HTTP request) -- it must commit here, before
        # handing off, or the freshly planned rows aren't visible yet.
        await self._session.commit()

        runnable_ids = [job.id for job in jobs if job.status == ToolExecutionStatus.PENDING]
        if runnable_ids:
            await self._manager.enqueue(assessment_id, runnable_ids)

        reads = [self._to_read(job) for job in await self._reload_with_relations([job.id for job in jobs])]
        return ExecuteResponse(
            assessment_id=assessment_id,
            jobs=reads,
            queued_count=len(runnable_ids),
            skipped_count=len(jobs) - len(runnable_ids),
        )

    async def cancel_job(self, job_id: uuid.UUID) -> JobRead:
        try:
            await self._manager.cancel(job_id)
        except JobNotFoundError as exc:
            raise NotFoundError(exc.args[0]) from exc
        except JobNotCancellableError as exc:
            raise ConflictError(exc.args[0]) from exc
        return await self.get_job(job_id)

    async def retry_job(self, job_id: uuid.UUID) -> JobRead:
        try:
            await self._manager.retry(job_id)
        except JobNotFoundError as exc:
            raise NotFoundError(exc.args[0]) from exc
        except JobNotRetriableError as exc:
            raise ConflictError(exc.args[0]) from exc
        return await self.get_job(job_id)

    # -- Queries --------------------------------------------------------------

    async def get_job(self, job_id: uuid.UUID) -> JobRead:
        job = await self._get_job_or_404(job_id)
        return self._to_read(job)

    async def list_jobs(
        self,
        *,
        assessment_id: uuid.UUID | None = None,
        status_filter: ToolExecutionStatus | None = None,
        tool_name: str | None = None,
        target_id: uuid.UUID | None = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> list[JobRead]:
        if sort_by not in _SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort jobs by '{sort_by}'.")

        conditions = [owned_by_active_assessment(ToolExecution.assessment_id)]
        if assessment_id is not None:
            conditions.append(ToolExecution.assessment_id == assessment_id)
        if status_filter is not None:
            conditions.append(ToolExecution.status == status_filter)
        if target_id is not None:
            conditions.append(ToolExecution.target_id == target_id)
        if tool_name is not None:
            conditions.append(ToolExecution.tool.has(name=tool_name))

        sort_column = getattr(ToolExecution, sort_by)
        order_by = sort_column.desc() if sort_desc else sort_column.asc()
        stmt = (
            select(ToolExecution)
            .options(selectinload(ToolExecution.target), selectinload(ToolExecution.tool))
            .where(*conditions)
            .order_by(order_by)
        )
        jobs = list((await self._session.execute(stmt)).scalars().all())
        return [self._to_read(job) for job in jobs]

    async def get_logs(self, job_id: uuid.UUID, *, tail: int | None = None, search: str | None = None) -> JobLogsResponse:
        job = await self._get_job_or_404(job_id)
        lines = ExecutionLogger.read(Path(job.log_path), tail_lines=tail, search=search) if job.log_path else []
        return JobLogsResponse(job_id=job_id, lines=lines, log_path=job.log_path)

    async def get_results(self, job_id: uuid.UUID) -> JobResultsResponse:
        """A job's normalized results -- empty lists for a tool that doesn't populate Hosts/Services/Observations.

        Since Phase 8, a ``DiscoveredHost`` no longer belongs to one execution --
        "which hosts did this job touch" is answered via the
        ``ExecutionHost`` join table, not a direct FK. The OS name/accuracy
        shown here is the host's single best-accuracy candidate across its
        *entire* history (not just this one job's own scan) since OS
        detection may have run on an earlier execution and that knowledge is
        still current -- durable, cumulative inventory, not a per-job snapshot.
        """
        await self._get_job_or_404(job_id)
        hosts_stmt = (
            select(DiscoveredHost)
            .join(ExecutionHost, ExecutionHost.host_id == DiscoveredHost.id)
            .options(selectinload(DiscoveredHost.services), selectinload(DiscoveredHost.operating_systems))
            .where(ExecutionHost.execution_id == job_id)
            .order_by(DiscoveredHost.created_at)
        )
        hosts = list((await self._session.execute(hosts_stmt)).scalars().all())
        observations_stmt = (
            select(Observation).where(Observation.execution_id == job_id).order_by(Observation.created_at)
        )
        observations = list((await self._session.execute(observations_stmt)).scalars().all())

        return JobResultsResponse(
            job_id=job_id,
            hosts=[self._to_host_read(host) for host in hosts],
            observations=[
                ObservationRead(
                    id=observation.id, host_id=observation.host_id, port=observation.port,
                    source=observation.source, title=observation.title, detail=observation.detail,
                )
                for observation in observations
            ],
        )

    @staticmethod
    def _to_host_read(host: DiscoveredHost) -> HostRead:
        best_os = max(host.operating_systems, key=lambda os: os.accuracy, default=None)
        return HostRead(
            id=host.id, ip_address=host.ipv4 or host.ipv6, hostname=host.hostname, mac_address=host.mac_address,
            mac_vendor=host.mac_vendor, state=host.state,
            os_name=best_os.name if best_os else None, os_accuracy=best_os.accuracy if best_os else None,
            services=[
                ServiceRead(
                    id=service.id, port=service.port, protocol=service.protocol, state=service.state,
                    service_name=service.service_name, product=service.product, version=service.version,
                    extra_info=service.extra_info,
                )
                for service in host.services
            ],
        )

    async def get_raw_output(self, job_id: uuid.UUID) -> RawOutputResponse:
        await self._get_job_or_404(job_id)
        stmt = select(RawToolOutput).where(RawToolOutput.execution_id == job_id).order_by(RawToolOutput.created_at.desc())
        raw_output = (await self._session.execute(stmt)).scalars().first()
        if raw_output is None:
            raise NotFoundError(f"Job {job_id} has no raw output recorded.")

        content = raw_output.raw_text
        if content is None and raw_output.file_path:
            path = Path(raw_output.file_path)
            content = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None

        return RawOutputResponse(job_id=job_id, format=raw_output.format, content=content, created_at=raw_output.created_at)

    async def get_progress(self, assessment_id: uuid.UUID) -> AssessmentProgress:
        await self._get_assessment_or_404(assessment_id)

        counts_stmt = (
            select(ToolExecution.status, func.count())
            .where(ToolExecution.assessment_id == assessment_id)
            .group_by(ToolExecution.status)
        )
        counts = {status: count for status, count in (await self._session.execute(counts_stmt)).all()}

        current_stmt = (
            select(ToolExecution)
            .options(selectinload(ToolExecution.target), selectinload(ToolExecution.tool))
            .where(ToolExecution.assessment_id == assessment_id, ToolExecution.status == ToolExecutionStatus.RUNNING)
            .order_by(ToolExecution.started_at.asc())
        )
        current_jobs = [self._to_read(job) for job in (await self._session.execute(current_stmt)).scalars().all()]

        total = sum(counts.values())
        finished = sum(
            counts.get(status, 0)
            for status in (
                ToolExecutionStatus.COMPLETED,
                ToolExecutionStatus.FAILED,
                ToolExecutionStatus.CANCELLED,
                ToolExecutionStatus.TIMEOUT,
                ToolExecutionStatus.SKIPPED,
            )
        )
        return AssessmentProgress(
            assessment_id=assessment_id,
            total=total,
            pending=counts.get(ToolExecutionStatus.PENDING, 0),
            queued=counts.get(ToolExecutionStatus.QUEUED, 0),
            preparing=counts.get(ToolExecutionStatus.PREPARING, 0),
            running=counts.get(ToolExecutionStatus.RUNNING, 0),
            completed=counts.get(ToolExecutionStatus.COMPLETED, 0),
            failed=counts.get(ToolExecutionStatus.FAILED, 0),
            cancelled=counts.get(ToolExecutionStatus.CANCELLED, 0),
            timeout=counts.get(ToolExecutionStatus.TIMEOUT, 0),
            skipped=counts.get(ToolExecutionStatus.SKIPPED, 0),
            percent_complete=round((finished / total) * 100, 1) if total else 0.0,
            current_jobs=current_jobs,
        )

    # -- Internal helpers -----------------------------------------------------

    async def _get_assessment_or_404(self, assessment_id: uuid.UUID) -> Assessment:
        stmt = select(Assessment).where(Assessment.id == assessment_id, Assessment.deleted_at.is_(None))
        assessment = (await self._session.execute(stmt)).scalar_one_or_none()
        if assessment is None:
            raise NotFoundError(f"Assessment {assessment_id} not found.")
        return assessment

    async def _get_job_or_404(self, job_id: uuid.UUID) -> ToolExecution:
        stmt = (
            select(ToolExecution)
            .options(selectinload(ToolExecution.target), selectinload(ToolExecution.tool))
            .where(ToolExecution.id == job_id)
        )
        job = (await self._session.execute(stmt)).scalar_one_or_none()
        if job is None:
            raise NotFoundError(f"Job {job_id} not found.")
        return job

    async def _reload_with_relations(self, job_ids: list[uuid.UUID]) -> list[ToolExecution]:
        if not job_ids:
            return []
        stmt = (
            select(ToolExecution)
            .options(selectinload(ToolExecution.target), selectinload(ToolExecution.tool))
            .where(ToolExecution.id.in_(job_ids))
        )
        by_id = {job.id: job for job in (await self._session.execute(stmt)).scalars().all()}
        return [by_id[job_id] for job_id in job_ids if job_id in by_id]

    @staticmethod
    def _to_read(job: ToolExecution) -> JobRead:
        return JobRead(
            id=job.id,
            assessment_id=job.assessment_id,
            target_id=job.target_id,
            target_value=job.target.target_value,
            tool_id=job.tool_id,
            tool_name=job.tool.name,
            status=job.status,
            status_message=job.status_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            duration=job.duration,
            return_code=job.return_code,
            retry_count=job.retry_count,
            log_path=job.log_path,
            profile_id=job.profile_id,
            generated_command=job.generated_command,
            created_at=job.created_at,
        )
