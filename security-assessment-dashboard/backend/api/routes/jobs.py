"""Job (``ToolExecution``) endpoints: list, inspect, cancel, retry, and read logs.

"Job" here is the execution engine's vocabulary for one ``ToolExecution``
row -- see ``backend/workers/__init__.py``. Planning/queuing a batch of
jobs happens via ``POST /assessments/{id}/execute`` (``backend.api.routes.assessments``),
not here.
"""

import uuid

from fastapi import APIRouter, Query

from backend.api.dependencies.services import ExecutionServiceDep
from backend.models.enums import ToolExecutionStatus
from backend.schemas.execution import JobLogsResponse, JobRead
from backend.schemas.scan_result import JobResultsResponse, RawOutputResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=list[JobRead], summary="List jobs, optionally filtered")
async def list_jobs(
    service: ExecutionServiceDep,
    assessment_id: uuid.UUID | None = Query(default=None),
    status_filter: ToolExecutionStatus | None = Query(default=None, alias="status"),
    tool_name: str | None = Query(default=None),
    target_id: uuid.UUID | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_desc: bool = Query(default=True),
) -> list[JobRead]:
    return await service.list_jobs(
        assessment_id=assessment_id,
        status_filter=status_filter,
        tool_name=tool_name,
        target_id=target_id,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )


@router.get("/{job_id}", response_model=JobRead, summary="Get one job")
async def get_job(job_id: uuid.UUID, service: ExecutionServiceDep) -> JobRead:
    return await service.get_job(job_id)


@router.get("/{job_id}/logs", response_model=JobLogsResponse, summary="Read one job's combined log file")
async def get_job_logs(
    job_id: uuid.UUID,
    service: ExecutionServiceDep,
    tail: int | None = Query(default=None, ge=1, description="Return only the last N lines."),
    search: str | None = Query(default=None, description="Case-insensitive substring filter."),
) -> JobLogsResponse:
    return await service.get_logs(job_id, tail=tail, search=search)


@router.get("/{job_id}/results", response_model=JobResultsResponse, summary="A job's normalized hosts/services/observations")
async def get_job_results(job_id: uuid.UUID, service: ExecutionServiceDep) -> JobResultsResponse:
    return await service.get_results(job_id)


@router.get("/{job_id}/raw-output", response_model=RawOutputResponse, summary="A job's raw, unmodified tool output")
async def get_job_raw_output(job_id: uuid.UUID, service: ExecutionServiceDep) -> RawOutputResponse:
    return await service.get_raw_output(job_id)


@router.post("/{job_id}/cancel", response_model=JobRead, summary="Cancel a queued or running job")
async def cancel_job(job_id: uuid.UUID, service: ExecutionServiceDep) -> JobRead:
    return await service.cancel_job(job_id)


@router.post("/{job_id}/retry", response_model=JobRead, summary="Re-queue a failed, cancelled, or timed-out job")
async def retry_job(job_id: uuid.UUID, service: ExecutionServiceDep) -> JobRead:
    return await service.retry_job(job_id)
