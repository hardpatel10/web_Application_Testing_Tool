"""Service layer for the Assessment Pipeline.

Thin HTTP-facing translation over :class:`~backend.pipeline.engine.PipelineEngine`
-- the same split as ``ExecutionService``/``backend.workers`` and
``CorrelationService``/``backend.correlation``: this module knows about
requests/responses/404s, the engine itself knows nothing about HTTP.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.exceptions import NotFoundError
from backend.models.assessment import Assessment
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import PipelineJobStatus
from backend.models.pipeline_job import PipelineJob
from backend.models.pipeline_run import PipelineRun
from backend.models.tool_execution import ToolExecution
from backend.pipeline.engine import PipelineEngine
from backend.pipeline.models import EXECUTION_STATUS_TO_PIPELINE_JOB_STATUS
from backend.plugins.manager.plugin_manager import PluginManager
from backend.schemas.pipeline import PipelineJobRead, PipelineRunRead, PipelineStartRequest
from backend.workers.manager import ExecutionManager


class PipelineService:
    """Business logic for starting and inspecting one assessment's Assessment Pipeline run(s)."""

    def __init__(self, session: AsyncSession, plugin_manager: PluginManager, execution_manager: ExecutionManager) -> None:
        self._session = session
        self._plugins = plugin_manager
        self._manager = execution_manager

    async def start_pipeline(self, assessment_id: uuid.UUID, payload: PipelineStartRequest) -> PipelineRunRead:
        await self._get_assessment_or_404(assessment_id)
        engine = PipelineEngine(self._session, self._plugins, self._manager)
        run = await engine.start(assessment_id, payload.target_id)
        return await self._to_read(run.id)

    async def get_pipeline(self, assessment_id: uuid.UUID) -> PipelineRunRead:
        await self._get_assessment_or_404(assessment_id)
        stmt = (
            select(PipelineRun)
            .where(PipelineRun.assessment_id == assessment_id)
            .order_by(PipelineRun.started_at.desc())
        )
        run = (await self._session.execute(stmt)).scalars().first()
        if run is None:
            raise NotFoundError(f"Assessment {assessment_id} has no Assessment Pipeline run yet.")
        return await self._to_read(run.id)

    async def _get_assessment_or_404(self, assessment_id: uuid.UUID) -> Assessment:
        stmt = select(Assessment).where(Assessment.id == assessment_id, Assessment.deleted_at.is_(None))
        assessment = (await self._session.execute(stmt)).scalar_one_or_none()
        if assessment is None:
            raise NotFoundError(f"Assessment {assessment_id} not found.")
        return assessment

    async def _to_read(self, run_id: uuid.UUID) -> PipelineRunRead:
        stmt = (
            select(PipelineRun)
            .options(selectinload(PipelineRun.jobs).selectinload(PipelineJob.host))
            .where(PipelineRun.id == run_id)
        )
        run = (await self._session.execute(stmt)).scalar_one()
        jobs = sorted(run.jobs, key=lambda job: job.created_at)
        live_statuses = await self._live_statuses_for(jobs)
        return PipelineRunRead(
            id=run.id,
            assessment_id=run.assessment_id,
            recon_execution_id=run.recon_execution_id,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            jobs=[
                PipelineJobRead(
                    id=job.id, stage=job.stage, tool_name=job.tool_name, host_id=job.host_id,
                    host_label=_host_label(job.host), service_id=job.service_id,
                    execution_id=job.execution_id, target_value=job.target_value,
                    status=live_statuses.get(job.id, job.status), skip_reason=job.skip_reason, created_at=job.created_at,
                )
                for job in jobs
            ],
        )

    async def _live_statuses_for(self, jobs: list[PipelineJob]) -> dict[uuid.UUID, PipelineJobStatus]:
        """A job's own ``status`` column is only re-stamped at its execution's *terminal*
        transition (see ``backend.workers.pipeline_hook``) -- nothing updates it on a mere
        PREPARING -> RUNNING transition, since only terminal transitions call back into the
        pipeline at all. Re-derive a live display status from the underlying ``ToolExecution``
        for any job still sitting at WAITING, so the graph shows "Running" while a scan (e.g. a
        multi-minute Nmap recon) is actually in progress, instead of "Waiting" the whole time.
        """
        pending_execution_ids = [job.execution_id for job in jobs if job.status == PipelineJobStatus.WAITING and job.execution_id]
        if not pending_execution_ids:
            return {}
        executions = (
            await self._session.execute(select(ToolExecution).where(ToolExecution.id.in_(pending_execution_ids)))
        ).scalars().all()
        status_by_execution_id = {execution.id: execution.status for execution in executions}
        return {
            job.id: EXECUTION_STATUS_TO_PIPELINE_JOB_STATUS[status_by_execution_id[job.execution_id]]
            for job in jobs
            if job.status == PipelineJobStatus.WAITING and job.execution_id in status_by_execution_id
        }


def _host_label(host: DiscoveredHost | None) -> str | None:
    if host is None:
        return None
    return host.hostname or host.fqdn or host.ipv4 or host.ipv6
