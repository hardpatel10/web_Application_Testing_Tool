"""Version information endpoint."""

from fastapi import APIRouter

from backend.api.dependencies.services import VersionServiceDep
from backend.schemas.version import VersionResponse

router = APIRouter(tags=["Version"])


@router.get("/version", response_model=VersionResponse, summary="Application version information")
def get_version(version_service: VersionServiceDep) -> VersionResponse:
    """Return application version, build identifier, and Python runtime version."""
    return version_service.get_version()
