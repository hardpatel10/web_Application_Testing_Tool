"""Findings API: read-only access to the Correlation Engine's output."""

import uuid

from fastapi import APIRouter, Query

from backend.api.dependencies.services import FindingQueryServiceDep
from backend.database.pagination import Pagination, Sort, SortDirection
from backend.models.enums import FindingConfidence, FindingSeverity, FindingStatus
from backend.schemas.common import PageResponse
from backend.schemas.finding import FindingDetailRead, FindingSummaryRead

router = APIRouter(prefix="/findings", tags=["Findings"])


@router.get("", response_model=PageResponse[FindingSummaryRead], summary="Search, filter, sort, and page findings")
async def list_findings(
    service: FindingQueryServiceDep,
    assessment_id: uuid.UUID | None = Query(default=None),
    host_id: uuid.UUID | None = Query(default=None),
    severity: FindingSeverity | None = Query(default=None),
    confidence: FindingConfidence | None = Query(default=None),
    status: FindingStatus | None = Query(default=None),
    category: str | None = Query(default=None),
    plugin: str | None = Query(default=None),
    rule_id: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Matches against title/description."),
    sort_by: str = Query(default="last_seen"),
    sort_dir: SortDirection = Query(default=SortDirection.DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> PageResponse[FindingSummaryRead]:
    result = await service.list_findings(
        assessment_id=assessment_id, host_id=host_id, severity=severity, confidence=confidence,
        status=status, category=category, plugin=plugin, rule_id=rule_id, search=search,
        sort=Sort(field=sort_by, direction=sort_dir), pagination=Pagination(page=page, page_size=page_size),
    )
    return PageResponse.from_page(result)


@router.get("/{finding_id}", response_model=FindingDetailRead, summary="Full finding detail")
async def get_finding(finding_id: uuid.UUID, service: FindingQueryServiceDep) -> FindingDetailRead:
    return await service.get_finding(finding_id)
