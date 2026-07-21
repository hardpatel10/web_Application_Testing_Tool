"""Service inventory endpoints: ports/protocols observed across all hosts. Read-only."""

import uuid

from fastapi import APIRouter, Query

from backend.api.dependencies.services import HostInventoryQueryServiceDep
from backend.database.pagination import Pagination, Sort, SortDirection
from backend.models.enums import NetworkProtocol, PortState
from backend.schemas.host_inventory import ServiceRead
from backend.schemas.common import PageResponse

router = APIRouter(prefix="/services", tags=["Services"])


@router.get("", response_model=PageResponse[ServiceRead], summary="Search, filter, sort, and page services")
async def list_services(
    service: HostInventoryQueryServiceDep,
    host_id: uuid.UUID | None = Query(default=None),
    protocol: NetworkProtocol | None = Query(default=None),
    state: PortState | None = Query(default=None),
    port: int | None = Query(default=None),
    search: str | None = Query(default=None, description="Matches against service_name/product."),
    sort_by: str = Query(default="last_seen"),
    sort_dir: SortDirection = Query(default=SortDirection.DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> PageResponse[ServiceRead]:
    result = await service.list_services(
        host_id=host_id,
        protocol=protocol,
        state=state,
        port=port,
        search=search,
        sort=Sort(field=sort_by, direction=sort_dir),
        pagination=Pagination(page=page, page_size=page_size),
    )
    return PageResponse.from_page(result)
