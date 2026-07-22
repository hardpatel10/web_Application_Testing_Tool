"""Bridges a job's terminal transition to the Assessment Pipeline, for jobs that belong to one.

Deliberately thin and defensive: the overwhelming majority of jobs (every
manual "Run Tools" execution) are *not* part of any :class:`~backend.models.pipeline_run.PipelineRun`,
so :func:`on_job_terminal` is a single indexed-miss query for them and does
nothing else. Only a job created by :class:`~backend.pipeline.engine.PipelineEngine`
itself (its ``execution_id`` set on a ``PipelineJob`` row) triggers any of
this.

This is the one place :mod:`backend.workers` reaches into pipeline/
correlation territory -- called from :meth:`~backend.workers.manager.ExecutionManager._on_job_terminal`,
which already does other direct, non-plugin-specific bookkeeping (cohort
tracking, assessment status flips) in the same spot. Per
``backend.services.correlation_service``'s own explicit rule ("never
invoked as a side effect of a completed job... never something
backend.workers calls into"), this module never calls
:class:`~backend.services.correlation_service.CorrelationService` itself --
only :class:`~backend.pipeline.engine.PipelineEngine` does that, and only
for jobs that belong to a pipeline run. A manual, ad-hoc execution still
requires the explicit ``POST /correlation/run`` button, exactly as before.
"""

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select

from backend.database.session import background_session
from backend.models.enums import PipelineJobStatus, PipelineStage, ToolExecutionStatus
from backend.models.pipeline_job import PipelineJob
from backend.pipeline.engine import PipelineEngine
from backend.plugins.manager.plugin_manager import PluginManager

if TYPE_CHECKING:
    from backend.workers.manager import ExecutionManager

logger = logging.getLogger(__name__)

_RECON_FAILURE_STATUSES = {ToolExecutionStatus.FAILED, ToolExecutionStatus.TIMEOUT, ToolExecutionStatus.CANCELLED}
_SCAN_TERMINAL_STATUSES = {
    ToolExecutionStatus.COMPLETED, ToolExecutionStatus.FAILED, ToolExecutionStatus.CANCELLED, ToolExecutionStatus.TIMEOUT,
}


async def on_job_terminal(
    plugin_manager: PluginManager, execution_manager: "ExecutionManager", job_id: uuid.UUID, status: ToolExecutionStatus
) -> None:
    """If ``job_id`` belongs to an active pipeline run, advance it. A no-op for every other job."""
    async with background_session() as session:
        pipeline_job = (
            await session.execute(select(PipelineJob).where(PipelineJob.execution_id == job_id))
        ).scalar_one_or_none()
        if pipeline_job is None:
            return

        pipeline_job.status = _map_status(status)
        engine = PipelineEngine(session, plugin_manager, execution_manager)

        try:
            if pipeline_job.stage is PipelineStage.RECON:
                if status is ToolExecutionStatus.COMPLETED:
                    await engine.advance_after_nmap(pipeline_job.pipeline_run_id, job_id)
                elif status in _RECON_FAILURE_STATUSES:
                    await engine.advance_after_recon_failure(pipeline_job.pipeline_run_id)
            elif pipeline_job.stage is PipelineStage.SCAN and status in _SCAN_TERMINAL_STATUSES:
                await engine.try_finalize(pipeline_job.pipeline_run_id)
        except Exception:
            logger.exception("Pipeline advancement failed for job %s (pipeline_run_id=%s)", job_id, pipeline_job.pipeline_run_id)


def _map_status(status: ToolExecutionStatus) -> PipelineJobStatus:
    if status is ToolExecutionStatus.COMPLETED:
        return PipelineJobStatus.COMPLETED
    if status is ToolExecutionStatus.SKIPPED:
        return PipelineJobStatus.SKIPPED
    return PipelineJobStatus.FAILED
