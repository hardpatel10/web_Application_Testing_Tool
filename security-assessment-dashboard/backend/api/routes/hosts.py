"""Discovered host inventory endpoints: the durable, deduplicated host list.

Read-only -- every row is written only by
:class:`backend.services.host_inventory_service.HostInventoryService` as a
side effect of a completed scan, never through this API. A host is a child
of the ``Target`` that discovered it (see ``backend.models.discovered_host``),
so ``target_id`` -- not just ``assessment_id`` -- is a first-class filter here.
"""

import uuid

from fastapi import APIRouter, Query

from backend.api.dependencies.services import HostInventoryQueryServiceDep
from backend.database.pagination import Pagination, Sort, SortDirection
from backend.models.enums import HostState, HostType
from backend.schemas.host_inventory import HostDetailRead, HostSummaryRead
from backend.schemas.common import PageResponse

router = APIRouter(prefix="/hosts", tags=["Discovered Hosts"])


@router.get("", response_model=PageResponse[HostSummaryRead], summary="Search, filter, sort, and page discovered hosts")
async def list_hosts(
    service: HostInventoryQueryServiceDep,
    assessment_id: uuid.UUID | None = Query(default=None),
    target_id: uuid.UUID | None = Query(default=None),
    host_type: HostType | None = Query(default=None),
    state: HostState | None = Query(default=None),
    search: str | None = Query(default=None, description="Matches against hostname/fqdn/ipv4/ipv6."),
    sort_by: str = Query(default="last_seen"),
    sort_dir: SortDirection = Query(default=SortDirection.DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> PageResponse[HostSummaryRead]:
    result = await service.list_hosts(
        assessment_id=assessment_id,
        target_id=target_id,
        host_type=host_type,
        state=state,
        search=search,
        sort=Sort(field=sort_by, direction=sort_dir),
        pagination=Pagination(page=page, page_size=page_size),
    )
    return PageResponse.from_page(result)


@router.get("/{host_id}", response_model=HostDetailRead, summary="Get one discovered host's full detail")
async def get_host(host_id: uuid.UUID, service: HostInventoryQueryServiceDep) -> HostDetailRead:
    return await service.get_host(host_id)
