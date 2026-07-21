"""Response schemas for the health endpoint."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Application liveness/status payload."""

    status: str = Field(description="Overall application status.", examples=["ok"])
    uptime_seconds: float = Field(description="Seconds since the application started.")
    version: str = Field(description="Application version.")
