"""Request/response schemas for Tool Management.

Distinct from ``backend.schemas.plugin`` (Phase 4's generic, framework-wide
plugin introspection API): these shapes are specific to the 15 supported
security tools, backed by the persistent ``Tool``/``ToolConfiguration``
DB rows rather than being purely in-memory.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.enums import RawOutputFormat, TargetType, ToolHealthStatus, ToolStatus


class ToolSummary(BaseModel):
    """One row of the Tool Management list view."""

    id: str
    name: str
    display_name: str
    version: str | None
    status: ToolStatus
    health_status: ToolHealthStatus | None
    enabled: bool
    is_installed: bool
    last_checked_at: datetime | None
    supported_targets: list[TargetType]
    supported_output_formats: list[RawOutputFormat]


class ToolConfigurationRead(BaseModel):
    """A tool's current configuration."""

    timeout: int | None
    working_directory: str | None
    custom_executable_path: str | None
    http_proxy: str | None
    https_proxy: str | None
    socks_proxy: str | None
    rate_limit: int | None
    retries: int | None
    output_directory: str | None
    temp_directory: str | None
    arguments: list[str]
    environment_variables: dict[str, str]
    wordlists: dict[str, str]


class ToolConfigurationUpdate(BaseModel):
    """Partial update payload for a tool's configuration. Omitted fields are left unchanged.

    ``enabled`` lives on the ``Tool`` row itself (not ``ToolConfiguration``)
    but is exposed here since there is no separate enable/disable endpoint
    and it is, conceptually, part of a tool's configuration.
    """

    enabled: bool | None = None
    timeout: int | None = Field(default=None, gt=0)
    working_directory: str | None = None
    custom_executable_path: str | None = None
    http_proxy: str | None = None
    https_proxy: str | None = None
    socks_proxy: str | None = None
    rate_limit: int | None = Field(default=None, gt=0)
    retries: int | None = Field(default=None, ge=0)
    output_directory: str | None = None
    temp_directory: str | None = None
    arguments: list[str] | None = None
    environment_variables: dict[str, str] | None = None
    wordlists: dict[str, str] | None = None


class ToolDetail(BaseModel):
    """Full detail for one tool."""

    id: str
    name: str
    display_name: str
    description: str
    homepage: str | None
    documentation_url: str | None
    install_instructions: dict[str, str] | None
    license: str
    version: str | None
    installation_path: str | None
    status: ToolStatus
    health_status: ToolHealthStatus | None
    health_message: str | None
    enabled: bool
    is_installed: bool
    last_checked_at: datetime | None
    supported_platforms: list[str]
    supported_targets: list[TargetType]
    supported_output_formats: list[RawOutputFormat]
    required_binaries: list[str]
    dependencies: list[str]
    missing_dependencies: list[str]
    configuration: ToolConfigurationRead
    validation_valid: bool
    validation_errors: list[str]
    validation_warnings: list[str]
    created_at: datetime


class ToolHealthResponse(BaseModel):
    """Result of a (fresh, live) health check."""

    name: str
    status: ToolHealthStatus
    installed: bool
    version_detected: str | None
    message: str | None
    checked_at: datetime


class ToolValidationResult(BaseModel):
    """Result of validating one tool's installation/configuration."""

    name: str
    valid: bool
    errors: list[str]
    warnings: list[str]


class ToolValidateRequest(BaseModel):
    """Optional scoping for a validation run. Validates every supported tool if ``name`` is omitted."""

    name: str | None = None


class ToolDiscoveryResponse(BaseModel):
    """Result of a full re-discovery/sync pass."""

    tools: list[ToolSummary]
    not_loaded: list[str] = Field(
        default_factory=list, description="Supported tool ids with no matching plugin currently registered."
    )


class FilesystemEntry(BaseModel):
    """One entry in a directory listing."""

    name: str
    path: str
    is_directory: bool


class FilesystemBrowseResponse(BaseModel):
    """A directory listing, for the wordlist/path picker."""

    path: str
    parent: str | None
    entries: list[FilesystemEntry]
