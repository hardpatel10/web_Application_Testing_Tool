"""Request/response schemas for the Assessment Execution Engine."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.enums import ToolExecutionStatus


class ToolExecutionOptionsSchema(BaseModel):
    """Per-tool planning options for one ``/execute`` call: a Scan Profile id and its overrides.

    Only meaningful for a plugin with a Scan Profile system (Nmap is the
    reference implementation) — naming a profile for a tool without one is
    a request-shape error, not a silent no-op.
    """

    profile_id: str | None = None
    advanced_options: dict | None = None


class ExecuteRequest(BaseModel):
    """Request body for ``POST /assessments/{id}/execute``."""

    tool_names: list[str] = Field(min_length=1, description="Plugin/tool ids to run, e.g. ['nmap'].")
    target_ids: list[uuid.UUID] | None = Field(
        default=None, description="Subset of the assessment's enabled targets. Omit to select all enabled targets."
    )
    tool_options: dict[str, ToolExecutionOptionsSchema] | None = Field(
        default=None, description="Keyed by tool name, e.g. {'nmap': {'profile_id': 'tcp_full'}}."
    )


class JobRead(BaseModel):
    """One job -- one ``ToolExecution`` row."""

    id: uuid.UUID
    assessment_id: uuid.UUID
    target_id: uuid.UUID
    target_value: str
    tool_id: uuid.UUID
    tool_name: str
    status: ToolExecutionStatus
    status_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration: float | None
    return_code: int | None
    retry_count: int
    log_path: str | None
    profile_id: str | None
    generated_command: list[str] | None
    created_at: datetime


class ExecuteResponse(BaseModel):
    """Result of planning and queuing one execution run."""

    assessment_id: uuid.UUID
    jobs: list[JobRead]
    queued_count: int
    skipped_count: int


class JobLogsResponse(BaseModel):
    """One job's combined log file, optionally filtered/tailed."""

    job_id: uuid.UUID
    lines: list[str]
    log_path: str | None


class AssessmentProgress(BaseModel):
    """Live counts of an assessment's jobs by status, plus what's running right now."""

    assessment_id: uuid.UUID
    total: int
    pending: int
    queued: int
    preparing: int
    running: int
    completed: int
    failed: int
    cancelled: int
    timeout: int
    skipped: int
    percent_complete: float = Field(description="Completed+failed+cancelled+timeout+skipped, as a percent of total.")
    current_jobs: list[JobRead]
