"""``PipelineEngine``: the Assessment Pipeline's write side.

Turns a completed Nmap execution's real, already-persisted ``Service`` rows
into decisions (via :class:`~backend.pipeline.registry.PipelineRuleRegistry`)
and those decisions into real, durable rows: synthetic endpoint ``Target``s,
planned/queued follow-up ``ToolExecution``s, plain skip ``Observation``s, and
the ``PipelineRun``/``PipelineJob`` execution-graph rows the frontend reads.

Deliberately reuses :class:`~backend.workers.planner.ExecutionPlanner` and
:class:`~backend.workers.manager.ExecutionManager` exactly as a manual
"Run Tools" request would -- a follow-up scanner that's disabled, not
installed, or unhealthy gets exactly the same ``SKIPPED`` treatment here,
for free, with no pipeline-specific reimplementation of that logic.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import AppException, NotFoundError
from backend.models.base import utcnow
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import (
    ObservationCategory,
    PipelineJobStatus,
    PipelineRunStatus,
    PipelineStage,
    TargetOrigin,
    TargetType,
    ToolExecutionStatus,
)
from backend.models.execution_host import ExecutionHost
from backend.models.observation import Observation
from backend.models.pipeline_job import PipelineJob
from backend.models.pipeline_run import PipelineRun
from backend.models.service import Service
from backend.models.target import Target
from backend.plugins.manager.plugin_manager import PluginManager
from backend.pipeline.models import EXECUTION_STATUS_TO_PIPELINE_JOB_STATUS, ScheduleDecision, SkipDecision
from backend.pipeline.registry import PipelineRuleRegistry, get_pipeline_rule_registry
from backend.services import fingerprinting
from backend.services.correlation_service import CorrelationService
from backend.workers.planner import ExecutionPlanner

if TYPE_CHECKING:
    # Deferred: backend.workers.manager imports backend.workers.pipeline_hook, which imports
    # this module -- a real top-level import here would be circular. ExecutionManager is only
    # ever used as a type hint (the real instance is injected by the caller), so this is safe.
    from backend.workers.manager import ExecutionManager

_RECON_TOOL_NAME = "nmap"
_WEB_TOOLS_ON_NO_WEB_SERVICE: tuple[str, ...] = ("nikto", "nuclei")
_TLS_TOOL_NAME = "sslscan"
_NO_TLS_SKIP_REASON = "Skipped by Pipeline: No TLS-enabled services discovered."

_SCAN_STAGE_TERMINAL = {
    PipelineJobStatus.COMPLETED, PipelineJobStatus.FAILED, PipelineJobStatus.SKIPPED,
}


class PipelineEngine:
    """Decides, schedules, and tracks one assessment's Assessment Pipeline run."""

    def __init__(
        self,
        session: AsyncSession,
        plugin_manager: PluginManager,
        execution_manager: "ExecutionManager",
        registry: PipelineRuleRegistry | None = None,
    ) -> None:
        self._session = session
        self._plugins = plugin_manager
        self._manager = execution_manager
        self._registry = registry or get_pipeline_rule_registry()

    # -- Start: plan + queue the recon (Nmap) job ------------------------------

    async def start(self, assessment_id: uuid.UUID, target_id: uuid.UUID) -> PipelineRun:
        target = await self._session.get(Target, target_id)
        if target is None or target.assessment_id != assessment_id:
            raise NotFoundError(f"Target {target_id} not found on assessment {assessment_id}.")

        run = PipelineRun(assessment_id=assessment_id, status=PipelineRunStatus.RUNNING, started_at=utcnow())
        self._session.add(run)
        await self._session.flush()

        planner = ExecutionPlanner(self._session, self._plugins)
        jobs = await planner.plan(assessment_id, [_RECON_TOOL_NAME], [target_id])
        nmap_job = jobs[0]
        run.recon_execution_id = nmap_job.id

        self._session.add(
            PipelineJob(
                pipeline_run_id=run.id, stage=PipelineStage.RECON, tool_name=_RECON_TOOL_NAME,
                execution_id=nmap_job.id, target_value=target.target_value,
                status=EXECUTION_STATUS_TO_PIPELINE_JOB_STATUS[nmap_job.status],
                skip_reason=nmap_job.status_message if nmap_job.status == ToolExecutionStatus.SKIPPED else None,
            )
        )
        await self._session.flush()

        if nmap_job.status != ToolExecutionStatus.PENDING:
            # Nmap itself couldn't even be planned (not installed/disabled/unhealthy/can't
            # validate this target) -- the pipeline never gets to advance past recon.
            run.status = PipelineRunStatus.FAILED
            run.completed_at = utcnow()
            return run

        # ExecutionManager.enqueue() reads/writes through its own background_session()
        # (a separate connection/transaction) -- must commit here first, same precedent
        # as ExecutionService.execute_assessment().
        await self._session.commit()
        await self._manager.enqueue(assessment_id, [nmap_job.id])
        return run

    # -- Advance after the recon (Nmap) job reaches a terminal status ---------

    async def advance_after_recon_failure(self, pipeline_run_id: uuid.UUID) -> None:
        """Nmap FAILED/TIMEOUT/CANCELLED -- do not run any follow-up scanner."""
        run = await self._session.get(PipelineRun, pipeline_run_id)
        if run is None:
            return
        for tool_name in (*_WEB_TOOLS_ON_NO_WEB_SERVICE, _TLS_TOOL_NAME):
            self._session.add(
                PipelineJob(
                    pipeline_run_id=run.id, stage=PipelineStage.SCAN, tool_name=tool_name,
                    status=PipelineJobStatus.SKIPPED,
                    skip_reason="Skipped by Pipeline: Nmap did not complete successfully.",
                )
            )
        run.status = PipelineRunStatus.FAILED
        run.completed_at = utcnow()

    async def advance_after_nmap(self, pipeline_run_id: uuid.UUID, nmap_execution_id: uuid.UUID) -> None:
        """Nmap COMPLETED -- decide and schedule every follow-up scanner."""
        run = await self._session.get(PipelineRun, pipeline_run_id)
        if run is None:
            return

        host_ids = (
            await self._session.execute(
                select(ExecutionHost.host_id).where(ExecutionHost.execution_id == nmap_execution_id)
            )
        ).scalars().all()

        for host_id in host_ids:
            host = await self._session.get(DiscoveredHost, host_id)
            if host is not None:
                await self._advance_host(run, host, nmap_execution_id)

        await self._session.flush()
        await self.try_finalize(pipeline_run_id)

    async def _advance_host(self, run: PipelineRun, host: DiscoveredHost, nmap_execution_id: uuid.UUID) -> None:
        services = list(
            (await self._session.execute(select(Service).where(Service.host_id == host.id))).scalars().all()
        )
        # Tracks "did any rule recognize any service on this host at all" -- a SkipDecision
        # (e.g. SSH/SMB/database) is just as much a recognized service as a ScheduleDecision;
        # only a host where *nothing* was recognized falls through to the generic "no
        # supported web services" message. Conflating the two was a real bug this suite's own
        # SSH-only-host test caught: an SSH-only host got both the correct SSH-specific skip
        # *and* a second, redundant "no web services" skip for the same two tools.
        any_recognized_service = False
        # Tracked independently of any_recognized_service: SSLScan gets its own dedicated skip
        # message whenever no TLS service was found, regardless of *why* -- an HTTP-only host, an
        # SSH/SMB/database-only host, and a host with no services at all must all produce the same
        # honest "no TLS-enabled services" SSLScan job, not silently omit it or reuse a message
        # about a different reason.
        any_tls_service = False
        for service in services:
            decision = self._registry.decide(service, host)
            if isinstance(decision, ScheduleDecision):
                any_recognized_service = True
                if _TLS_TOOL_NAME in decision.tool_names:
                    any_tls_service = True
                for tool_name in decision.tool_names:
                    await self._schedule_follow_up(run, host, service, nmap_execution_id, tool_name, decision.endpoint)
            elif isinstance(decision, SkipDecision):
                any_recognized_service = True
                await self._record_skip(run, host, service, decision)

        if not any_recognized_service:
            for tool_name in _WEB_TOOLS_ON_NO_WEB_SERVICE:
                self._session.add(
                    PipelineJob(
                        pipeline_run_id=run.id, stage=PipelineStage.SCAN, tool_name=tool_name,
                        host_id=host.id, status=PipelineJobStatus.SKIPPED,
                        skip_reason="No supported web services discovered.",
                    )
                )

        if not any_tls_service:
            self._session.add(
                PipelineJob(
                    pipeline_run_id=run.id, stage=PipelineStage.SCAN, tool_name=_TLS_TOOL_NAME,
                    host_id=host.id, status=PipelineJobStatus.SKIPPED, skip_reason=_NO_TLS_SKIP_REASON,
                )
            )

    async def _schedule_follow_up(
        self,
        run: PipelineRun,
        host: DiscoveredHost,
        service: Service,
        nmap_execution_id: uuid.UUID,
        tool_name: str,
        endpoint: str,
    ) -> None:
        target = await self._get_or_create_pipeline_target(run.assessment_id, endpoint, nmap_execution_id)
        planner = ExecutionPlanner(self._session, self._plugins)
        try:
            jobs = await planner.plan(run.assessment_id, [tool_name], [target.id])
        except AppException as exc:
            # No running HTTP request is watching this call (it runs from the job-terminal
            # hook, see backend.workers.pipeline_hook) -- a tool with no catalog row at all
            # (tool discovery never run) must degrade to a visible, honest skip node, not an
            # unhandled exception that leaves the run stuck RUNNING forever.
            self._session.add(
                PipelineJob(
                    pipeline_run_id=run.id, stage=PipelineStage.SCAN, tool_name=tool_name,
                    host_id=host.id, service_id=service.id, target_value=endpoint,
                    status=PipelineJobStatus.SKIPPED, skip_reason=exc.message,
                )
            )
            return
        job = jobs[0]
        self._session.add(
            PipelineJob(
                pipeline_run_id=run.id, stage=PipelineStage.SCAN, tool_name=tool_name,
                host_id=host.id, service_id=service.id, execution_id=job.id, target_value=endpoint,
                status=EXECUTION_STATUS_TO_PIPELINE_JOB_STATUS[job.status],
                skip_reason=job.status_message if job.status == ToolExecutionStatus.SKIPPED else None,
            )
        )
        if job.status == ToolExecutionStatus.PENDING:
            await self._session.commit()
            await self._manager.enqueue(run.assessment_id, [job.id])

    async def _get_or_create_pipeline_target(
        self, assessment_id: uuid.UUID, endpoint: str, nmap_execution_id: uuid.UUID
    ) -> Target:
        existing = (
            await self._session.execute(
                select(Target).where(Target.assessment_id == assessment_id, Target.target_value == endpoint)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        target = Target(
            assessment_id=assessment_id, target_type=TargetType.URL, target_value=endpoint,
            origin=TargetOrigin.PIPELINE, discovered_from_execution_id=nmap_execution_id,
        )
        self._session.add(target)
        await self._session.flush()
        return target

    async def _record_skip(
        self, run: PipelineRun, host: DiscoveredHost, service: Service, decision: SkipDecision
    ) -> None:
        for tool_name in decision.reserved_tool_names:
            self._session.add(
                PipelineJob(
                    pipeline_run_id=run.id, stage=PipelineStage.SCAN, tool_name=tool_name,
                    host_id=host.id, service_id=service.id, status=PipelineJobStatus.SKIPPED,
                    skip_reason=decision.reason,
                )
            )
        await self._get_or_create_skip_observation(host, decision)

    async def _get_or_create_skip_observation(self, host: DiscoveredHost, decision: SkipDecision) -> None:
        """Record the skip as a plain, neutral fact -- get-or-create so re-running the pipeline never duplicates it."""
        fp = fingerprinting.observation_fingerprint(
            plugin="pipeline-engine", host_fingerprint_value=host.fingerprint,
            category=decision.category.value, observation_type=decision.rule_id, title=decision.reason,
        )
        existing = (
            await self._session.execute(
                select(Observation).where(Observation.host_id == host.id, Observation.fingerprint == fp)
            )
        ).scalar_one_or_none()
        now = utcnow()
        if existing is not None:
            existing.last_seen = now
            return
        self._session.add(
            Observation(
                host_id=host.id, plugin="pipeline-engine", source="pipeline-engine",
                category=decision.category, observation_type=decision.rule_id,
                title=decision.reason, detail=None, fingerprint=fp, first_seen=now, last_seen=now,
            )
        )

    # -- Finalize: once every scan-stage job is terminal, correlate ------------

    async def try_finalize(self, pipeline_run_id: uuid.UUID) -> None:
        run = await self._session.get(PipelineRun, pipeline_run_id)
        if run is None or run.status != PipelineRunStatus.RUNNING:
            return

        scan_jobs = list(
            (
                await self._session.execute(
                    select(PipelineJob).where(
                        PipelineJob.pipeline_run_id == run.id, PipelineJob.stage == PipelineStage.SCAN
                    )
                )
            ).scalars().all()
        )
        if not scan_jobs or any(job.status not in _SCAN_STAGE_TERMINAL for job in scan_jobs):
            return

        await self._session.flush()
        await CorrelationService(self._session).correlate_assessment(run.assessment_id)

        completed_at = utcnow()
        self._session.add(
            PipelineJob(
                pipeline_run_id=run.id, stage=PipelineStage.CORRELATE, tool_name=None,
                status=PipelineJobStatus.COMPLETED,
            )
        )
        run.status = PipelineRunStatus.COMPLETED
        run.completed_at = completed_at
