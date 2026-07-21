"""Observation inventory endpoints: neutral, non-vulnerability facts. Read-only.

Per ``.claude/CLAUDE.md``: no severity/confidence filter exists here because
none exists on the model -- an Observation is a fact, never a judged finding.
"""

import uuid

from fastapi import APIRouter, Query

from backend.api.dependencies.services import HostInventoryQueryServiceDep
from backend.database.pagination import Pagination, Sort, SortDirection
from backend.models.enums import ObservationCategory
from backend.schemas.host_inventory import ObservationRead
from backend.schemas.common import PageResponse

router = APIRouter(prefix="/observations", tags=["Observations"])


@router.get("", response_model=PageResponse[ObservationRead], summary="Search, filter, sort, and page observations")
async def list_observations(
    service: HostInventoryQueryServiceDep,
    host_id: uuid.UUID | None = Query(default=None),
    service_id: uuid.UUID | None = Query(default=None),
    category: ObservationCategory | None = Query(default=None),
    plugin: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Matches against title/detail."),
    sort_by: str = Query(default="last_seen"),
    sort_dir: SortDirection = Query(default=SortDirection.DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> PageResponse[ObservationRead]:
    result = await service.list_observations(
        host_id=host_id,
        service_id=service_id,
        category=category,
        plugin=plugin,
        search=search,
        sort=Sort(field=sort_by, direction=sort_dir),
        pagination=Pagination(page=page, page_size=page_size),
    )
    return PageResponse.from_page(result)
