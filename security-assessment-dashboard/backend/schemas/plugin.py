"""Request/response schemas for the plugin management API.

These are the HTTP-facing shapes. The plugin framework's own domain
models (``backend.plugins.models.*``) are framework-internal and
FastAPI/HTTP-agnostic by design; ``PluginService`` is what adapts one to
the other, the same boundary role ``TargetService`` plays between the ORM
and ``backend.schemas.target``.
"""

from datetime import datetime

from pydantic import BaseModel

from backend.models.enums import RawOutputFormat, TargetType
from backend.plugins.models.enums import PluginHealthStatus, SupportedPlatform


class PluginSummary(BaseModel):
    """One row of the plugin list view."""

    id: str
    display_name: str
    version: str
    author: str
    enabled: bool
    installed: bool
    validation_valid: bool


class PluginConfigurationResponse(BaseModel):
    """A plugin's current runtime configuration."""

    enabled: bool
    default_timeout_seconds: int
    working_directory: str | None
    arguments: list[str]
    environment_variables: dict[str, str]
    temp_directory: str | None


class PluginDetail(BaseModel):
    """Full detail for one plugin."""

    id: str
    display_name: str
    version: str
    author: str
    description: str
    homepage: str | None
    license: str
    supported_platforms: list[SupportedPlatform]
    supported_targets: list[TargetType]
    supported_output_formats: list[RawOutputFormat]
    required_binaries: list[str]
    documentation_url: str | None
    dependencies: list[str]
    missing_dependencies: list[str]
    config: PluginConfigurationResponse
    validation_valid: bool
    validation_errors: list[str]
    validation_warnings: list[str]
    source_path: str
    loaded_at: datetime


class PluginHealthResponse(BaseModel):
    """A plugin's runtime health check result."""

    plugin_id: str
    status: PluginHealthStatus
    installed: bool
    version_detected: str | None
    message: str | None
    checked_at: datetime


class PluginValidationResponse(BaseModel):
    """Result of re-running structure/manifest/interface validation."""

    plugin_id: str
    valid: bool
    errors: list[str]
    warnings: list[str]


class PluginDiscoveryFailure(BaseModel):
    """One plugin directory that failed to load during discovery."""

    directory: str
    error: str


class PluginReloadResponse(BaseModel):
    """Result of a full plugin re-discovery."""

    registered_count: int
    plugins: list[PluginSummary]
    failures: list[PluginDiscoveryFailure]
