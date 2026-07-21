"""Target management endpoints, nested under one assessment."""

import uuid
from typing import Literal

from fastapi import APIRouter, File, Query, Response, UploadFile
from fastapi import status as http_status

from backend.api.dependencies.services import TargetServiceDep
from backend.database.pagination import Pagination, Sort, SortDirection
from backend.models.enums import TargetType
from backend.schemas.common import PageResponse
from backend.schemas.target import (
    TargetBulkImportResult,
    TargetCreate,
    TargetDuplicateRequest,
    TargetRead,
    TargetUpdate,
    TargetValidateRequest,
    TargetValidateResponse,
)

router = APIRouter(prefix="/assessments/{assessment_id}/targets", tags=["Targets"])

#: Workspace-wide targets endpoint, mounted separately from the nested
#: per-assessment CRUD router above -- the Assessment Target is the platform's
#: real assessment scope (per .claude/CLAUDE.md's corrected domain model), so
#: it needs its own top-level list/nav surface, mirroring /hosts.
top_level_router = APIRouter(prefix="/targets", tags=["Targets"])


@top_level_router.get("", response_model=PageResponse[TargetRead], summary="Search, filter, sort, and page targets across every assessment")
async def list_all_targets(
    service: TargetServiceDep,
    assessment_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, description="Matches against target_value."),
    target_type: TargetType | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_dir: SortDirection = Query(default=SortDirection.DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> PageResponse[TargetRead]:
    result = await service.list_all(
        assessment_id=assessment_id,
        search=search,
        target_type_filter=target_type,
        enabled_filter=enabled,
        sort=Sort(field=sort_by, direction=sort_dir),
        pagination=Pagination(page=page, page_size=page_size),
    )
    return PageResponse.from_page(result)


@router.get("", response_model=PageResponse[TargetRead], summary="Search, filter, sort, and page an assessment's targets")
async def list_targets(
    assessment_id: uuid.UUID,
    service: TargetServiceDep,
    search: str | None = Query(default=None, description="Matches against target_value."),
    target_type: TargetType | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_dir: SortDirection = Query(default=SortDirection.DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> PageResponse[TargetRead]:
    result = await service.list(
        assessment_id,
        search=search,
        target_type_filter=target_type,
        enabled_filter=enabled,
        sort=Sort(field=sort_by, direction=sort_dir),
        pagination=Pagination(page=page, page_size=page_size),
    )
    return PageResponse.from_page(result)


@router.post("", response_model=TargetRead, status_code=http_status.HTTP_201_CREATED, summary="Add a target")
async def create_target(assessment_id: uuid.UUID, payload: TargetCreate, service: TargetServiceDep) -> TargetRead:
    return await service.create(assessment_id, payload)


@router.post("/validate", response_model=TargetValidateResponse, summary="Validate a target value without saving it")
async def validate_target(payload: TargetValidateRequest, service: TargetServiceDep) -> TargetValidateResponse:
    return service.validate(payload)


@router.post(
    "/bulk-import",
    response_model=TargetBulkImportResult,
    summary="Bulk-import targets from a TXT (one per line) or CSV file",
)
async def bulk_import_targets(
    assessment_id: uuid.UUID, service: TargetServiceDep, file: UploadFile = File(...)
) -> TargetBulkImportResult:
    content = await file.read()
    return await service.bulk_import(assessment_id, file.filename or "import.txt", content)


@router.get("/export", summary="Export all of an assessment's targets as a TXT or CSV file")
async def export_targets(
    assessment_id: uuid.UUID, service: TargetServiceDep, format: Literal["txt", "csv"] = Query(default="txt")
) -> Response:
    content = await service.export(assessment_id, format)
    media_type = "text/csv" if format == "csv" else "text/plain"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="targets.{format}"'},
    )


@router.get("/{target_id}", response_model=TargetRead, summary="Get one target")
async def get_target(assessment_id: uuid.UUID, target_id: uuid.UUID, service: TargetServiceDep) -> TargetRead:
    return await service.get(assessment_id, target_id)


@router.put("/{target_id}", response_model=TargetRead, summary="Update a target")
async def update_target(
    assessment_id: uuid.UUID, target_id: uuid.UUID, payload: TargetUpdate, service: TargetServiceDep
) -> TargetRead:
    return await service.update(assessment_id, target_id, payload)


@router.delete("/{target_id}", status_code=http_status.HTTP_204_NO_CONTENT, summary="Delete a target")
async def delete_target(assessment_id: uuid.UUID, target_id: uuid.UUID, service: TargetServiceDep) -> None:
    await service.delete(assessment_id, target_id)


@router.post("/{target_id}/enable", response_model=TargetRead, summary="Enable a target")
async def enable_target(assessment_id: uuid.UUID, target_id: uuid.UUID, service: TargetServiceDep) -> TargetRead:
    return await service.set_enabled(assessment_id, target_id, True)


@router.post("/{target_id}/disable", response_model=TargetRead, summary="Disable a target")
async def disable_target(assessment_id: uuid.UUID, target_id: uuid.UUID, service: TargetServiceDep) -> TargetRead:
    return await service.set_enabled(assessment_id, target_id, False)


@router.post(
    "/{target_id}/duplicate",
    response_model=TargetRead,
    status_code=http_status.HTTP_201_CREATED,
    summary="Duplicate a target under a new value",
)
async def duplicate_target(
    assessment_id: uuid.UUID, target_id: uuid.UUID, payload: TargetDuplicateRequest, service: TargetServiceDep
) -> TargetRead:
    return await service.duplicate(assessment_id, target_id, payload.target_value)
