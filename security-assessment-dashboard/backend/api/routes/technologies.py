"""Technology inventory endpoints: normalized software/product signatures. Read-only."""

import uuid

from fastapi import APIRouter, Query

from backend.api.dependencies.services import HostInventoryQueryServiceDep
from backend.database.pagination import Pagination, Sort, SortDirection
from backend.models.enums import TechnologyCategory
from backend.schemas.host_inventory import TechnologyRead
from backend.schemas.common import PageResponse

router = APIRouter(prefix="/technologies", tags=["Technologies"])


@router.get("", response_model=PageResponse[TechnologyRead], summary="Search, filter, sort, and page technologies")
async def list_technologies(
    service: HostInventoryQueryServiceDep,
    host_id: uuid.UUID | None = Query(default=None),
    category: TechnologyCategory | None = Query(default=None),
    search: str | None = Query(default=None, description="Matches against name."),
    sort_by: str = Query(default="last_seen"),
    sort_dir: SortDirection = Query(default=SortDirection.DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> PageResponse[TechnologyRead]:
    result = await service.list_technologies(
        host_id=host_id,
        category=category,
        search=search,
        sort=Sort(field=sort_by, direction=sort_dir),
        pagination=Pagination(page=page, page_size=page_size),
    )
    return PageResponse.from_page(result)
