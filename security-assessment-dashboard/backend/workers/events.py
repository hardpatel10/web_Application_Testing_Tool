"""In-process execution event bus.

Decouples ``backend.workers.manager.ExecutionManager`` (which decides
*when* something noteworthy happened to a job or an assessment's
execution run) from the things that care -- structured per-job logging
and the assessment activity log. No message broker or persistence of its
own: subscribers are plain async callables invoked in-process, in
registration order, per the phase's "everything executes locally"
constraint.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class ExecutionEventType(StrEnum):
    """Kind of noteworthy occurrence during job/assessment execution."""

    ASSESSMENT_EXECUTION_STARTED = "assessment_execution_started"
    ASSESSMENT_EXECUTION_FINISHED = "assessment_execution_finished"
    ASSESSMENT_EXECUTION_CANCELLED = "assessment_execution_cancelled"
    JOB_QUEUED = "job_queued"
    JOB_PREPARING = "job_preparing"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    JOB_TIMEOUT = "job_timeout"
    JOB_SKIPPED = "job_skipped"
    JOB_RETRIED = "job_retried"


@dataclass(frozen=True)
class ExecutionEvent:
    """One occurrence, ready to be logged and/or persisted."""

    event_type: ExecutionEventType
    assessment_id: uuid.UUID
    message: str
    job_id: uuid.UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


ExecutionEventHandler = Callable[[ExecutionEvent], Awaitable[None]]


class ExecutionEventBus:
    """Publishes :class:`ExecutionEvent`\\ s to every subscribed handler, in order."""

    def __init__(self) -> None:
        self._handlers: list[ExecutionEventHandler] = []

    def subscribe(self, handler: ExecutionEventHandler) -> None:
        self._handlers.append(handler)

    async def publish(self, event: ExecutionEvent) -> None:
        for handler in self._handlers:
            await handler(event)
