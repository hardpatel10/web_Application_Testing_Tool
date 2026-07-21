"""Health check endpoint."""

from fastapi import APIRouter

from backend.api.dependencies.services import AppStartTimeDep, HealthServiceDep
from backend.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Application health status")
def get_health(
    health_service: HealthServiceDep,
    start_time: AppStartTimeDep,
) -> HealthResponse:
    """Return application status, uptime, and version."""
    return health_service.get_health(start_time)
