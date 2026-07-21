"""Service layer for application health status."""

from backend.core.config import Settings
from backend.schemas.health import HealthResponse
from backend.utils.time_utils import seconds_since


class HealthService:
    """Computes application liveness status."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_health(self, start_time: float) -> HealthResponse:
        return HealthResponse(
            status="ok",
            uptime_seconds=round(seconds_since(start_time), 3),
            version=self._settings.app_version,
        )
