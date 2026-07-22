"""Request/response schemas for the Assessment Pipeline."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.enums import PipelineJobStatus, PipelineRunStatus, PipelineStage


class PipelineStartRequest(BaseModel):
    """Request body for ``POST /assessments/{id}/pipeline/start``."""

    target_id: uuid.UUID = Field(description="Which of the assessment's own targets to run recon against.")


class PipelineJobRead(BaseModel):
    """One execution-graph node."""

    id: uuid.UUID
    stage: PipelineStage
    tool_name: str | None
    host_id: uuid.UUID | None
    host_label: str | None = Field(default=None, description="Denormalized hostname/IP for display, e.g. grouping by host in a graph.")
    service_id: uuid.UUID | None
    execution_id: uuid.UUID | None
    target_value: str | None
    status: PipelineJobStatus
    skip_reason: str | None
    created_at: datetime


class PipelineRunRead(BaseModel):
    """One Assessment Pipeline run and its full execution graph."""

    id: uuid.UUID
    assessment_id: uuid.UUID
    recon_execution_id: uuid.UUID | None
    status: PipelineRunStatus
    started_at: datetime
    completed_at: datetime | None
    jobs: list[PipelineJobRead]
