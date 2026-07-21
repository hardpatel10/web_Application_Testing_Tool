"""Per-plugin runtime configuration.

Held in-memory by the :class:`~backend.plugins.registry.plugin_registry.PluginRegistry`
alongside each registered plugin. Phase 5 promotes this to a DB-backed
model (``backend.models.tool.ToolConfiguration``) now that a real
configuration UI exists — ``backend.services.tool_service.ToolService``
is the only place that translates between the two; this class itself
still has no knowledge of the database.
"""

from pathlib import Path

from pydantic import BaseModel, Field


class PluginConfiguration(BaseModel):
    """Configuration governing how a plugin is enabled and invoked."""

    enabled: bool = True
    default_timeout_seconds: int = Field(default=300, gt=0)
    working_directory: Path | None = None
    custom_executable_path: Path | None = Field(
        default=None, description="User-specified executable override; takes precedence over auto-discovery."
    )
    arguments: list[str] = Field(default_factory=list)
    environment_variables: dict[str, str] = Field(default_factory=dict)
    temp_directory: Path | None = None
    output_directory: Path | None = None
    http_proxy: str | None = None
    https_proxy: str | None = None
    socks_proxy: str | None = None
    rate_limit: int | None = Field(default=None, gt=0, description="Requests/probes per second, tool-interpreted.")
    retries: int | None = Field(default=None, ge=0)
    wordlists: dict[str, Path] = Field(
        default_factory=dict, description="Wordlist slot name (e.g. 'directory', 'subdomains') to file path."
    )
    disabled_profile_ids: list[str] = Field(
        default_factory=list,
        description="Scan Profile ids (built-in or custom) the user has disabled for this plugin. "
        "A disabled profile still exists and can be viewed/exported, it just won't be offered for new scans.",
    )
