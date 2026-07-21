"""Response schemas for the version endpoint."""

from pydantic import BaseModel, Field


class VersionResponse(BaseModel):
    """Application and runtime version information."""

    version: str = Field(description="Application version.")
    build: str = Field(description="Build identifier, typically a short git commit hash.")
    python_version: str = Field(description="Python interpreter version running the server.")
