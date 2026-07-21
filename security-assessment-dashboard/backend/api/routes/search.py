"""Global search endpoint: hostname/IP/service/technology/observation, in one query."""

from fastapi import APIRouter, Query

from backend.api.dependencies.services import HostInventoryQueryServiceDep
from backend.schemas.host_inventory import SearchResponse

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResponse, summary="Search across hostname/IP, service, technology, and observation")
async def search(service: HostInventoryQueryServiceDep, q: str = Query(min_length=1)) -> SearchResponse:
    return await service.search(q)
