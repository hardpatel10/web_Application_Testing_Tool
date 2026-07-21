"""ExecutionManager: the job dispatcher and worker pool.

Owns the only asyncio machinery that actually runs jobs -- a bounded pool
of concurrent workers (an ``asyncio.Semaphore``, never a process pool or
external broker, per this phase's "everything executes locally, no
Celery/Redis/RabbitMQ/Kafka/multiprocessing" constraint), pulling job ids
off an :class:`~backend.workers.queue.ExecutionQueue` and, for each,
loading its ``ToolExecution`` row and calling into the target plugin's
``prepare()``/``build_command()``/``execute()``/``cleanup()`` -- never
any tool-specific logic of its own -- persisting status/timestamps/
output paths as the job progresses, and publishing
:class:`~backend.workers.events.ExecutionEvent`\\ s.

A module-level singleton, mirroring
``backend.plugins.manager.plugin_manager.get_plugin_manager`` -- this is
mutable, long-lived, in-process state (running tasks, a dispatcher loop),
not a cached pure function of its inputs.

Process control: "pause"/"resume" a single already-running job's OS
process is not something ``asyncio`` (or Windows, this project's
explicitly named target platform -- there is no ``SIGSTOP``/``SIGCONT``
equivalent for an arbitrary child process without fragile, unsupported
WinAPI thread-suspension tricks) can do safely or portably. What *is*
real and implemented here: cancel (stop a queued job before it starts, or
cancel a running job's ``asyncio.Task``), kill (escalate a stuck
terminate via ``backend.plugins.sdk.process_runner.terminate_process``
for any future subprocess-based plugin), retry, and timeout. See
``DECISIONS.md`` for this scoping call.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path

from backend.core.config import Settings
from backend.core.paths import assessment_directory
from backend.database.session import background_session
from backend.models.assessment import Assessment
from backend.models.base import utcnow
from backend.models.enums import AssessmentHistoryEventType, AssessmentStatus, ToolExecutionStatus
from backend.models.raw_tool_output import RawToolOutput
from backend.models.target import Target
from backend.models.tool import Tool
from backend.models.tool_execution import ToolExecution
from backend.plugins.manager.plugin_manager import PluginManager
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.models.normalized import NormalizedOutput
from backend.plugins.registry.registered_plugin import RegisteredPlugin
from backend.services.assessment_history_logger import log_assessment_event
from backend.services.host_inventory_service import HostInventoryService
from backend.workers.events import ExecutionEvent, ExecutionEventBus, ExecutionEventType
from backend.workers.exceptions import JobNotCancellableError, JobNotFoundError, JobNotRetriableError
from backend.workers.logger import ExecutionLogger
from backend.workers.queue import RETRY_PRIORITY, ExecutionQueue
from backend.workers.state import ACTIVE_STATUSES, RETRIABLE_STATUSES, TERMINAL_STATUSES

logger = logging.getLogger(__name__)

_TERMINAL_EVENTS = {
    ToolExecutionStatus.COMPLETED: ExecutionEventType.JOB_COMPLETED,
    ToolExecutionStatus.FAILED: ExecutionEventType.JOB_FAILED,
    ToolExecutionStatus.TIMEOUT: ExecutionEventType.JOB_TIMEOUT,
    ToolExecutionStatus.CANCELLED: ExecutionEventType.JOB_CANCELLED,
}


class ExecutionManager:
    """Dispatches queued jobs onto a bounded pool of asyncio workers."""

    def __init__(self, settings: Settings, plugin_manager: PluginManager) -> None:
        self._settings = settings
        self._plugins = plugin_manager
        self._queue = ExecutionQueue()
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_executions)
        self._dispatcher_task: asyncio.Task | None = None
        self._running_tasks: dict[uuid.UUID, asyncio.Task] = {}
        # Per-assessment "current execution run" bookkeeping: which jobs from
        # the most recent enqueue()/retry() haven't reached a terminal state
        # yet, and what each of those that has finished ended up as -- used
        # solely to decide when to fire ASSESSMENT_EXECUTION_FINISHED/CANCELLED
        # and flip Assessment.status back. A single in-flight run per
        # assessment is assumed (fine for a single-user local app); a second
        # concurrent /execute call on the same assessment replaces tracking
        # for the first.
        self._cohort_pending: dict[uuid.UUID, set[uuid.UUID]] = {}
        self._cohort_statuses: dict[uuid.UUID, dict[uuid.UUID, ToolExecutionStatus]] = {}
        # Strong references for the fire-and-forget safety-net tasks spawned
        # by _on_worker_done -- otherwise asyncio only holds a weak reference
        # to a task nothing awaits, and it can be garbage-collected mid-flight.
        # Self-removing via each task's own done callback.
        self._finalize_safety_net_tasks: set[asyncio.Task] = set()

        self.events = ExecutionEventBus()
        self.events.subscribe(self._log_event)
        self.events.subscribe(self._persist_coarse_history_event)

    # -- Public API used by ExecutionService --------------------------------

    def ensure_dispatcher_running(self) -> None:
        if self._dispatcher_task is None or self._dispatcher_task.done():
            self._dispatcher_task = asyncio.create_task(self._dispatch_loop())

    async def enqueue(self, assessment_id: uuid.UUID, job_ids: list[uuid.UUID]) -> None:
        """Queue every job id in ``job_ids`` and ensure the dispatcher is running."""
        if not job_ids:
            return
        self._cohort_pending[assessment_id] = set(job_ids)
        self._cohort_statuses[assessment_id] = {}

        async with background_session() as session:
            for job_id in job_ids:
                job = await session.get(ToolExecution, job_id)
                job.status = ToolExecutionStatus.QUEUED
            await self._mark_assessment_running(session, assessment_id)

        for job_id in job_ids:
            await self._queue.enqueue(job_id)
        self.ensure_dispatcher_running()

        await self.events.publish(
            ExecutionEvent(
                ExecutionEventType.ASSESSMENT_EXECUTION_STARTED, assessment_id, f"{len(job_ids)} job(s) queued."
            )
        )

    async def cancel(self, job_id: uuid.UUID) -> None:
        """Cancel a job: dequeue-and-skip if no worker owns it yet, ``Task.cancel()`` if one does.

        Whether a worker "owns" the job is decided by ``job_id in
        self._running_tasks`` -- set the instant ``_dispatch_loop`` spawns
        its task, not by the DB status being exactly ``RUNNING``. A job in
        ``PREPARING`` already has a live task concurrently mutating its
        row through its own ``background_session()`` calls; directly
        overwriting the DB row here for anything a task already owns
        would race that task and get silently clobbered the moment it
        next writes (observed while testing: a job cancelled during
        ``PREPARING`` kept running to completion because nothing told its
        task to stop).
        """
        # Both calls are synchronous (no ``await`` between them), so no
        # dispatcher interleaving can happen in between: cancel_queued()
        # is a harmless no-op if the job was never queued or was already
        # dequeued, and is_running() reflects the true state at this instant.
        self._queue.cancel_queued(job_id)
        owned_by_worker = self.is_running(job_id)

        async with background_session() as session:
            job = await session.get(ToolExecution, job_id)
            if job is None:
                raise JobNotFoundError(f"Job {job_id} not found.")
            if job.status not in ACTIVE_STATUSES:
                raise JobNotCancellableError(f"Job is {job.status.value} and cannot be cancelled.")
            assessment_id = job.assessment_id
            if not owned_by_worker:
                job.status = ToolExecutionStatus.CANCELLED
                job.completed_at = utcnow()
                job.status_message = "Cancelled before it started running."

        if owned_by_worker:
            task = self._running_tasks.get(job_id)
            if task is not None:
                task.cancel()
        else:
            await self.events.publish(
                ExecutionEvent(ExecutionEventType.JOB_CANCELLED, assessment_id, "Job cancelled.", job_id)
            )
            await self._on_job_terminal(assessment_id, job_id, ToolExecutionStatus.CANCELLED)

    async def retry(self, job_id: uuid.UUID) -> None:
        """Reset a failed/cancelled/timed-out job and re-queue it, ahead of freshly planned jobs."""
        async with background_session() as session:
            job = await session.get(ToolExecution, job_id)
            if job is None:
                raise JobNotFoundError(f"Job {job_id} not found.")
            if job.status not in RETRIABLE_STATUSES:
                raise JobNotRetriableError(f"Job is {job.status.value} and cannot be retried.")
            job.status = ToolExecutionStatus.QUEUED
            job.retry_count += 1
            job.started_at = None
            job.completed_at = None
            job.duration = None
            job.return_code = None
            job.status_message = None
            assessment_id = job.assessment_id
            await self._mark_assessment_running(session, assessment_id)

        self._cohort_pending.setdefault(assessment_id, set()).add(job_id)
        self._cohort_statuses.setdefault(assessment_id, {})
        await self._queue.enqueue(job_id, priority=RETRY_PRIORITY)
        self.ensure_dispatcher_running()
        await self.events.publish(
            ExecutionEvent(ExecutionEventType.JOB_RETRIED, assessment_id, "Job re-queued for retry.", job_id)
        )

    def is_running(self, job_id: uuid.UUID) -> bool:
        return job_id in self._running_tasks

    def queue_size(self) -> int:
        return self._queue.qsize()

    async def shutdown(self) -> None:
        """Cancel the dispatcher loop and every in-flight job worker; await their exit.

        Called on application shutdown (see ``backend.main``'s lifespan) so
        no ``asyncio.Task`` outlives the event loop it was created on --
        the same reason the backend test suite calls this between tests
        instead of leaking each test's tasks into the next test's loop.
        """
        cancellable = list(self._running_tasks.values())
        if self._dispatcher_task is not None:
            cancellable.append(self._dispatcher_task)
        for task in cancellable:
            task.cancel()
        if cancellable:
            await asyncio.gather(*cancellable, return_exceptions=True)
        self._running_tasks.clear()
        self._dispatcher_task = None

        # _on_worker_done's safety-net tasks are spawned from a done callback,
        # so cancelling `cancellable` above can create *new* entries in
        # _finalize_safety_net_tasks after this method's own task list was
        # already built -- a fixed snapshot-then-gather (the previous version
        # of this method) missed those, leaking a task that outlives this
        # event loop and surfaces as "Event loop is closed" from an orphaned
        # aiosqlite background thread once the loop actually closes (caught
        # by this test suite running back-to-back tests, each on its own
        # loop). These are quick DB writes, not long-running work, so we
        # *wait* for them rather than cancel them -- cancelling one mid-write
        # would just reproduce the exact "stuck in a non-terminal status"
        # class of bug it exists to fix, one level down. Loop (with a
        # checkpoint in between) since a just-finished safety-net task's own
        # done callback could theoretically still be scheduled when we first
        # check.
        while self._finalize_safety_net_tasks:
            await asyncio.gather(*list(self._finalize_safety_net_tasks), return_exceptions=True)
            await asyncio.sleep(0)

    # -- Dispatch loop --------------------------------------------------------

    async def _dispatch_loop(self) -> None:
        while True:
            job_id = await self._queue.dequeue()
            await self._semaphore.acquire()
            task = asyncio.create_task(self._run_job(job_id))
            self._running_tasks[job_id] = task
            task.add_done_callback(lambda _task, job_id=job_id: self._on_worker_done(job_id))

    def _on_worker_done(self, job_id: uuid.UUID) -> None:
        self._running_tasks.pop(job_id, None)
        self._semaphore.release()
        # Safety net, not the common path: normally _execute_job's own
        # try/except already left the job in a terminal status by now (either
        # a real outcome, or CANCELLED via its own asyncio.CancelledError
        # handler). But asyncio.Task.cancel() called before a task has run
        # even one line never actually enters the coroutine's frame at all --
        # verified directly: a try/except wrapping the *entire* body of a
        # coroutine does not fire if the task is cancelled before its first
        # step, so no code inside _run_job/_execute_job can ever observe that
        # cancellation. A done callback, in contrast, always fires once a
        # task is done for any reason, including that one -- this is the only
        # reliable place left to catch a job that would otherwise be stuck at
        # QUEUED/PREPARING/RUNNING forever. _ensure_cancelled_finalized() is a
        # no-op once the job is already terminal, which is the normal case.
        task = asyncio.create_task(self._ensure_cancelled_finalized(job_id))
        self._finalize_safety_net_tasks.add(task)
        task.add_done_callback(self._finalize_safety_net_tasks.discard)

    async def _run_job(self, job_id: uuid.UUID) -> None:
        try:
            await self._execute_job(job_id)
        except asyncio.CancelledError:
            pass  # finalized inside _execute_job, or by _on_worker_done's safety net
        except Exception:
            logger.exception("Unexpected error running job %s", job_id)

    async def _ensure_cancelled_finalized(self, job_id: uuid.UUID) -> None:
        async with background_session() as session:
            job = await session.get(ToolExecution, job_id)
            if job is None or job.status in TERMINAL_STATUSES:
                return
            assessment_id = job.assessment_id
        await self._finalize(
            job_id, assessment_id, ToolExecutionStatus.CANCELLED,
            status_message="Cancelled before it started running.",
        )

    async def _execute_job(self, job_id: uuid.UUID) -> None:
        # Every local a `finally`/`except` clause below might touch is seeded
        # here, before the `try`, and guarded at each use site -- the whole
        # method body (including the very first DB read that flips the job to
        # PREPARING) now sits inside one `try`, so a cancellation delivered at
        # *any* point still reaches the `except asyncio.CancelledError` branch
        # and gets finalized. A previous version's `try` only started after
        # that first read+write had already completed, so a job cancelled
        # before then raised straight through `_run_job`'s blanket
        # `except asyncio.CancelledError: pass` and was left stuck at QUEUED
        # or PREPARING forever -- caught by this test suite's
        # `test_cancel_queued_job_before_it_starts`, which is deliberately
        # racy about when the cancel lands.
        job_logger: ExecutionLogger | None = None
        registered = None
        context: PluginExecutionContext | None = None
        assessment_id: uuid.UUID | None = None
        timeout_seconds: float | None = None
        # Tracked locally (not re-read from a reloaded ORM row) so
        # duration math always subtracts two Python datetimes this same
        # coroutine produced -- SQLite's DATETIME storage round-trips a
        # ``DateTime(timezone=True)`` value as offset-naive, so comparing
        # a freshly reloaded ``job.started_at`` against a new
        # ``utcnow()`` would raise "can't subtract offset-naive and
        # offset-aware datetimes".
        started_at: datetime | None = None
        try:
            async with background_session() as session:
                job = await session.get(ToolExecution, job_id)
                if job is None or job.status != ToolExecutionStatus.QUEUED:
                    return  # cancelled or removed between dequeue and dispatch
                target = await session.get(Target, job.target_id)
                tool = await session.get(Tool, job.tool_id)
                assessment_id = job.assessment_id
                profile_id = job.profile_id
                advanced_options = job.advanced_options
                job.status = ToolExecutionStatus.PREPARING

            registered = self._plugins.get_plugin(tool.name)
            assessment_root = assessment_directory(self._settings.assessment_root_dir, assessment_id)
            output_dir = assessment_root / "raw" / str(job_id)
            log_path = assessment_root / "logs" / f"{job_id}.log"
            job_logger = ExecutionLogger(log_path)
            job_logger.write(f"Preparing job {job_id}: tool='{tool.name}' target='{target.target_value}'.")
            await self.events.publish(
                ExecutionEvent(ExecutionEventType.JOB_PREPARING, assessment_id, f"Preparing '{tool.name}'.", job_id)
            )

            timeout_seconds = registered.config.default_timeout_seconds
            context = PluginExecutionContext(
                target_type=target.target_type,
                target_value=target.target_value,
                output_directory=output_dir,
                timeout_seconds=timeout_seconds,
                extra_arguments=list(registered.config.arguments),
                profile_id=profile_id,
                advanced_options=advanced_options,
            )

            registered.instance.prepare(context)
            command = registered.instance.build_command(context)
            job_logger.write(f"Command: {' '.join(command)}")

            started_at = utcnow()
            async with background_session() as session:
                job = await session.get(ToolExecution, job_id)
                job.status = ToolExecutionStatus.RUNNING
                job.started_at = started_at
                job.generated_command = command
            job_logger.write("Job started.")
            await self.events.publish(
                ExecutionEvent(ExecutionEventType.JOB_STARTED, assessment_id, f"Running '{tool.name}'.", job_id)
            )

            raw_output = await asyncio.wait_for(registered.instance.execute(command, context), timeout=timeout_seconds)
        except TimeoutError:
            await self._finalize(
                job_id, assessment_id, ToolExecutionStatus.TIMEOUT, started_at=started_at,
                status_message=f"Exceeded its {timeout_seconds}s timeout.", job_logger=job_logger,
            )
            return
        except asyncio.CancelledError:
            await self._finalize(
                job_id, assessment_id, ToolExecutionStatus.CANCELLED, started_at=started_at,
                status_message="Cancelled while running." if started_at else "Cancelled before it started running.",
                job_logger=job_logger,
            )
            raise
        except Exception as exc:
            if job_logger is not None:
                job_logger.write(f"Unhandled exception: {exc}", level="ERROR")
            await self._finalize(
                job_id, assessment_id, ToolExecutionStatus.FAILED, started_at=started_at,
                status_message=str(exc), job_logger=job_logger,
            )
            return
        finally:
            if registered is not None and context is not None:
                try:
                    registered.instance.cleanup(context)
                except Exception:
                    logger.exception("cleanup() raised for job %s", job_id)

        output_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = output_dir / "stdout.txt"
        stderr_path = output_dir / "stderr.txt"
        stdout_path.write_text(raw_output.stdout, encoding="utf-8")
        stderr_path.write_text(raw_output.stderr, encoding="utf-8")
        job_logger.write_block("stdout", raw_output.stdout)
        job_logger.write_block("stderr", raw_output.stderr)

        succeeded = raw_output.exit_code == 0
        status = ToolExecutionStatus.COMPLETED if succeeded else ToolExecutionStatus.FAILED
        message = None if succeeded else f"Exit code {raw_output.exit_code}: {raw_output.stderr.strip()[:500]}"

        if succeeded:
            await self._persist_scan_results(job_id, assessment_id, registered, raw_output, output_dir, job_logger)

        await self._finalize(
            job_id, assessment_id, status, started_at=started_at,
            status_message=message, job_logger=job_logger, return_code=raw_output.exit_code,
            stdout_path=stdout_path, stderr_path=stderr_path, log_path=log_path,
        )

    async def _persist_scan_results(
        self,
        job_id: uuid.UUID,
        assessment_id: uuid.UUID,
        registered: RegisteredPlugin,
        raw_output: PluginRawOutput,
        output_dir: Path,
        job_logger: ExecutionLogger,
    ) -> None:
        """Parse + normalize a completed job's output and persist it, generically.

        Every completed job gets its raw output persisted as a
        ``RawToolOutput`` row, regardless of tool. Structured inventory rows
        are only created if the plugin's ``normalize()`` actually returned a
        :class:`~backend.plugins.models.normalized.NormalizedOutput` --
        true for Nmap (Phase 7's reference implementation), false for every
        detection-only tool (``execute()`` still refuses, so this method is
        never reached for them) and for ``dummy-execution`` (returns its own
        unrelated shape). A parse/normalize failure is logged and otherwise
        swallowed: the job already succeeded and its raw output is safe on
        disk -- CLAUDE.md's "only display real collected data" means a
        parsing hiccup must never fabricate structured results, not that it
        should fail an otherwise-successful job.

        The actual merge/upsert into the durable Host Inventory (dedup
        across repeated scans, execution history, technology/OS extraction)
        is :class:`~backend.services.host_inventory_service.HostInventoryService`'s
        job, not this dispatcher's -- keeps this package tool-agnostic
        dispatch only, per its own architectural role.
        """
        try:
            parsed = registered.instance.parse(raw_output)
            normalized = registered.instance.normalize(parsed)
        except Exception:
            logger.exception("parse()/normalize() raised for job %s", job_id)
            job_logger.write("Output parsing failed; raw output is preserved.", level="WARNING")
            normalized = None

        raw_output_path = None
        if raw_output.stdout:
            extension = raw_output.output_format.value
            raw_output_path = output_dir / f"output.{extension}"
            raw_output_path.write_text(raw_output.stdout, encoding="utf-8")

        async with background_session() as session:
            if raw_output_path is not None:
                session.add(
                    RawToolOutput(execution_id=job_id, format=raw_output.output_format, file_path=str(raw_output_path))
                )

            if isinstance(normalized, NormalizedOutput):
                summary = await HostInventoryService(session).persist(
                    assessment_id=assessment_id,
                    execution_id=job_id,
                    plugin_name=registered.manifest.id,
                    normalized=normalized,
                )
                job_logger.write(
                    f"Normalized: {summary.hosts_created} new host(s), {summary.hosts_updated} updated; "
                    f"{summary.services_created} new service(s), {summary.services_updated} updated; "
                    f"{summary.technologies_created} new technology(ies), {summary.operating_systems_created} new OS candidate(s); "
                    f"{summary.observations_created} new observation(s), {summary.observations_updated} re-observed."
                )

    async def _finalize(
        self, job_id, assessment_id: uuid.UUID | None, status, *, started_at=None,
        status_message=None, job_logger: ExecutionLogger | None = None, return_code=None,
        stdout_path=None, stderr_path=None, log_path=None,
    ) -> None:
        completed_at = utcnow()
        async with background_session() as session:
            job = await session.get(ToolExecution, job_id)
            if assessment_id is None:
                # Cancelled before _execute_job ever loaded the job (so it
                # never learned the assessment id itself) -- the row still has it.
                assessment_id = job.assessment_id
            job.status = status
            job.completed_at = completed_at
            job.duration = (completed_at - started_at).total_seconds() if started_at else None
            job.status_message = status_message
            job.return_code = return_code
            if stdout_path is not None:
                job.stdout_path = str(stdout_path)
            if stderr_path is not None:
                job.stderr_path = str(stderr_path)
            if log_path is not None:
                job.log_path = str(log_path)

        if job_logger is not None:
            level = "ERROR" if status in (ToolExecutionStatus.FAILED, ToolExecutionStatus.TIMEOUT) else "INFO"
            job_logger.write(f"Job finished: {status.value}." + (f" {status_message}" if status_message else ""), level=level)

        await self.events.publish(ExecutionEvent(_TERMINAL_EVENTS[status], assessment_id, status_message or status.value, job_id))
        await self._on_job_terminal(assessment_id, job_id, status)

    # -- Assessment-level run tracking --------------------------------------

    @staticmethod
    async def _mark_assessment_running(session, assessment_id: uuid.UUID) -> None:
        assessment = await session.get(Assessment, assessment_id)
        if assessment is None or assessment.status == AssessmentStatus.RUNNING:
            return
        assessment.previous_status = assessment.status
        assessment.status = AssessmentStatus.RUNNING
        if assessment.started_at is None:
            assessment.started_at = utcnow()
        await log_assessment_event(
            session, assessment_id, AssessmentHistoryEventType.EXECUTION_STARTED, "Execution run started."
        )

    async def _on_job_terminal(self, assessment_id: uuid.UUID, job_id: uuid.UUID, status: ToolExecutionStatus) -> None:
        pending = self._cohort_pending.get(assessment_id)
        if pending is None:
            return
        pending.discard(job_id)
        self._cohort_statuses[assessment_id][job_id] = status
        if pending:
            return

        statuses = self._cohort_statuses.pop(assessment_id)
        del self._cohort_pending[assessment_id]
        all_cancelled = bool(statuses) and all(s == ToolExecutionStatus.CANCELLED for s in statuses.values())
        await self._finalize_assessment(assessment_id, cancelled=all_cancelled)

    async def _finalize_assessment(self, assessment_id: uuid.UUID, *, cancelled: bool) -> None:
        async with background_session() as session:
            assessment = await session.get(Assessment, assessment_id)
            if assessment is None:
                return
            if cancelled:
                assessment.status = assessment.previous_status or AssessmentStatus.READY
                assessment.previous_status = None
                message = "Execution run cancelled."
                event_type_db = AssessmentHistoryEventType.EXECUTION_CANCELLED
                event_type_bus = ExecutionEventType.ASSESSMENT_EXECUTION_CANCELLED
            else:
                assessment.status = AssessmentStatus.COMPLETED
                assessment.previous_status = None
                assessment.completed_at = utcnow()
                message = "Execution run finished."
                event_type_db = AssessmentHistoryEventType.EXECUTION_FINISHED
                event_type_bus = ExecutionEventType.ASSESSMENT_EXECUTION_FINISHED
            await log_assessment_event(session, assessment_id, event_type_db, message)

        await self.events.publish(ExecutionEvent(event_type_bus, assessment_id, message))

    # -- Event subscribers ----------------------------------------------------

    @staticmethod
    async def _log_event(event: ExecutionEvent) -> None:
        logger.info(
            "%s: %s",
            event.event_type.value,
            event.message,
            extra={"extra_fields": {"assessment_id": str(event.assessment_id), "job_id": str(event.job_id) if event.job_id else None}},
        )

    @staticmethod
    async def _persist_coarse_history_event(event: ExecutionEvent) -> None:
        """Persist only job-level *failures* to the assessment activity log.

        Routine per-job milestones (queued/preparing/started/completed)
        stay in the job's own log file and the structured application
        log -- persisting all of them to ``assessment_history_entries``
        would drown a run's genuinely important lifecycle events
        (created/archived/etc.) in one row per job per state transition.
        Assessment-level start/finish/cancel events are already persisted
        directly by ``_mark_assessment_running``/``_finalize_assessment``.
        """
        if event.event_type is not ExecutionEventType.JOB_FAILED:
            return
        async with background_session() as session:
            await log_assessment_event(session, event.assessment_id, AssessmentHistoryEventType.JOB_FAILED, event.message)


_manager: ExecutionManager | None = None


def get_execution_manager(settings: Settings, plugin_manager: PluginManager) -> ExecutionManager:
    """Return the process-wide :class:`ExecutionManager`, constructing it on first access.

    Mirrors ``backend.plugins.manager.plugin_manager.get_plugin_manager``'s
    module-level singleton pattern -- mutable in-process state (running
    tasks, the dispatch loop), not a cached pure function of its inputs.
    """
    global _manager
    if _manager is None:
        _manager = ExecutionManager(settings, plugin_manager)
    return _manager


async def shutdown_execution_manager() -> None:
    """Gracefully stop the process-wide manager, if one was ever created. A no-op otherwise."""
    global _manager
    if _manager is not None:
        await _manager.shutdown()
        _manager = None
