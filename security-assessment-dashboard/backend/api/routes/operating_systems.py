"""Operating system inventory endpoints: every OS candidate match. Read-only.

Every candidate Nmap (or a future OS-fingerprinting plugin) reports is kept,
not just the single best match -- see ``backend.models.operating_system``.
"""

import uuid

from fastapi import APIRouter, Query

from backend.api.dependencies.services import HostInventoryQueryServiceDep
from backend.database.pagination import Pagination, Sort, SortDirection
from backend.schemas.host_inventory import OperatingSystemRead
from backend.schemas.common import PageResponse

router = APIRouter(prefix="/operating-systems", tags=["Operating Systems"])


@router.get("", response_model=PageResponse[OperatingSystemRead], summary="Search, filter, sort, and page OS candidate matches")
async def list_operating_systems(
    service: HostInventoryQueryServiceDep,
    host_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, description="Matches against name."),
    sort_by: str = Query(default="accuracy"),
    sort_dir: SortDirection = Query(default=SortDirection.DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> PageResponse[OperatingSystemRead]:
    result = await service.list_operating_systems(
        host_id=host_id,
        search=search,
        sort=Sort(field=sort_by, direction=sort_dir),
        pagination=Pagination(page=page, page_size=page_size),
    )
    return PageResponse.from_page(result)
