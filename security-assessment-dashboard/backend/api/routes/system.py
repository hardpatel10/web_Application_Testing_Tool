"""System information endpoint."""

from fastapi import APIRouter

from backend.api.dependencies.services import SystemInfoServiceDep
from backend.schemas.system import SystemResponse

router = APIRouter(tags=["System"])


@router.get("/system", response_model=SystemResponse, summary="Real host system information")
def get_system(system_info_service: SystemInfoServiceDep) -> SystemResponse:
    """Return real operating system, hardware, and memory information."""
    return system_info_service.get_system_info()
