"""Pure, DB-session-free shapes exchanged between the Pipeline Engine and its rules.

Mirrors :mod:`backend.correlation.models`'s split: a rule receives whatever
it needs to make a decision and returns a plain, inert decision object --
:class:`~backend.pipeline.engine.PipelineEngine` is the only place a
decision becomes a persisted ``Target``/``ToolExecution``/``PipelineJob``/
``Observation`` row.
"""

from dataclasses import dataclass, field

from backend.models.enums import ObservationCategory, PipelineJobStatus, ToolExecutionStatus

#: How a ``ToolExecution``'s real status maps onto the execution graph's own, smaller status
#: vocabulary (see ``PipelineJobStatus``'s docstring). Shared between ``PipelineEngine`` (which
#: stamps a ``PipelineJob``'s status once, at creation and at its own terminal transition) and
#: ``PipelineService`` (which re-derives a *live* display status for a still-WAITING job from its
#: underlying execution's current status, since nothing re-stamps the row on a mere
#: PREPARING->RUNNING transition -- only terminal transitions call back into the pipeline at all).
EXECUTION_STATUS_TO_PIPELINE_JOB_STATUS: dict[ToolExecutionStatus, PipelineJobStatus] = {
    ToolExecutionStatus.PENDING: PipelineJobStatus.WAITING,
    ToolExecutionStatus.QUEUED: PipelineJobStatus.WAITING,
    ToolExecutionStatus.PREPARING: PipelineJobStatus.WAITING,
    ToolExecutionStatus.RUNNING: PipelineJobStatus.RUNNING,
    ToolExecutionStatus.COMPLETED: PipelineJobStatus.COMPLETED,
    ToolExecutionStatus.FAILED: PipelineJobStatus.FAILED,
    ToolExecutionStatus.CANCELLED: PipelineJobStatus.FAILED,
    ToolExecutionStatus.TIMEOUT: PipelineJobStatus.FAILED,
    ToolExecutionStatus.SKIPPED: PipelineJobStatus.SKIPPED,
}


@dataclass(frozen=True, slots=True)
class ScheduleDecision:
    """Schedule one or more tools against one generated endpoint."""

    tool_names: tuple[str, ...]
    endpoint: str


@dataclass(frozen=True, slots=True)
class SkipDecision:
    """Explicitly decline to scan this service, with a human-readable reason.

    ``reserved_tool_names`` names the scanner(s) this decision stands in
    for (e.g. ``("nikto", "nuclei")`` for an SSH port) purely so the
    execution graph can render one node per tool the brief expects to see
    marked "Skipped" -- never actually scheduled. ``rule_id``/``category``
    back the plain ``Observation`` the engine records alongside the skip.
    """

    reason: str
    rule_id: str
    category: ObservationCategory
    reserved_tool_names: tuple[str, ...] = field(default_factory=tuple)


#: A rule's verdict on one service: schedule it, explicitly skip it, or (``None``)
#: decline to make any claim at all, leaving room for another rule to evaluate it.
PipelineDecision = ScheduleDecision | SkipDecision | None
