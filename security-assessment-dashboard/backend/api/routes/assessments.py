"""Assessment management endpoints."""

import uuid

from fastapi import APIRouter, Query
from fastapi import status as http_status

from backend.api.dependencies.services import AssessmentServiceDep, ExecutionServiceDep
from backend.database.pagination import Pagination, Sort, SortDirection
from backend.schemas.assessment import (
    AssessmentCreate,
    AssessmentDuplicateRequest,
    AssessmentHistoryEntryRead,
    AssessmentRead,
    AssessmentUpdate,
)
from backend.schemas.common import PageResponse
from backend.schemas.execution import AssessmentProgress, ExecuteRequest, ExecuteResponse
from backend.models.enums import AssessmentStatus, AssessmentType

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.get("", response_model=PageResponse[AssessmentRead], summary="Search, filter, sort, and page assessments")
async def list_assessments(
    service: AssessmentServiceDep,
    search: str | None = Query(default=None, description="Matches against name or description."),
    status: AssessmentStatus | None = Query(default=None),
    assessment_type: AssessmentType | None = Query(default=None),
    tags: list[str] | None = Query(default=None, description="Assessments matching any of the given tags."),
    sort_by: str = Query(default="created_at"),
    sort_dir: SortDirection = Query(default=SortDirection.DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PageResponse[AssessmentRead]:
    result = await service.list(
        search=search,
        status_filter=status,
        assessment_type_filter=assessment_type,
        tags_filter=tags,
        sort=Sort(field=sort_by, direction=sort_dir),
        pagination=Pagination(page=page, page_size=page_size),
    )
    return PageResponse.from_page(result)


@router.post("", response_model=AssessmentRead, status_code=http_status.HTTP_201_CREATED, summary="Create an assessment")
async def create_assessment(payload: AssessmentCreate, service: AssessmentServiceDep) -> AssessmentRead:
    return await service.create(payload)


@router.get("/{assessment_id}", response_model=AssessmentRead, summary="Get one assessment")
async def get_assessment(assessment_id: uuid.UUID, service: AssessmentServiceDep) -> AssessmentRead:
    return await service.get(assessment_id)


@router.put("/{assessment_id}", response_model=AssessmentRead, summary="Update an assessment")
async def update_assessment(assessment_id: uuid.UUID, payload: AssessmentUpdate, service: AssessmentServiceDep) -> AssessmentRead:
    return await service.update(assessment_id, payload)


@router.delete("/{assessment_id}", status_code=http_status.HTTP_204_NO_CONTENT, summary="Soft-delete an assessment")
async def delete_assessment(assessment_id: uuid.UUID, service: AssessmentServiceDep) -> None:
    await service.delete(assessment_id)


@router.post("/{assessment_id}/archive", response_model=AssessmentRead, summary="Archive an assessment")
async def archive_assessment(assessment_id: uuid.UUID, service: AssessmentServiceDep) -> AssessmentRead:
    return await service.archive(assessment_id)


@router.post("/{assessment_id}/restore", response_model=AssessmentRead, summary="Restore an archived assessment")
async def restore_assessment(assessment_id: uuid.UUID, service: AssessmentServiceDep) -> AssessmentRead:
    return await service.restore(assessment_id)


@router.post(
    "/{assessment_id}/duplicate",
    response_model=AssessmentRead,
    status_code=http_status.HTTP_201_CREATED,
    summary="Duplicate an assessment, its tags, and its targets",
)
async def duplicate_assessment(
    assessment_id: uuid.UUID, payload: AssessmentDuplicateRequest, service: AssessmentServiceDep
) -> AssessmentRead:
    return await service.duplicate(assessment_id, payload)


@router.get(
    "/{assessment_id}/history",
    response_model=PageResponse[AssessmentHistoryEntryRead],
    summary="Get an assessment's activity log, newest first",
)
async def get_assessment_history(
    assessment_id: uuid.UUID,
    service: AssessmentServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PageResponse[AssessmentHistoryEntryRead]:
    result = await service.get_history(assessment_id, Pagination(page=page, page_size=page_size))
    return PageResponse.from_page(result)


@router.post(
    "/{assessment_id}/execute",
    response_model=ExecuteResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Plan and queue jobs (one per selected target x selected tool)",
)
async def execute_assessment(
    assessment_id: uuid.UUID, payload: ExecuteRequest, service: ExecutionServiceDep
) -> ExecuteResponse:
    return await service.execute_assessment(assessment_id, payload)


@router.get(
    "/{assessment_id}/progress",
    response_model=AssessmentProgress,
    summary="Live job counts by status, plus whatever is running right now",
)
async def get_assessment_progress(assessment_id: uuid.UUID, service: ExecutionServiceDep) -> AssessmentProgress:
    return await service.get_progress(assessment_id)
