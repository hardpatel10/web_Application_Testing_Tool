"""Diagnostics snapshot for one plugin's detection/version/health pipeline.

Returned by ``DetectionOnlyPlugin.diagnostics()`` (shared by every tool
plugin -- one implementation, not fifteen). Pure data: no I/O happens when
constructing this model, all of it is gathered by the caller first.
"""

from datetime import datetime

from pydantic import BaseModel

from backend.plugins.models.enums import PluginHealthStatus


class PluginDiagnostics(BaseModel):
    """Everything the Diagnostics tab needs to explain *why* a tool is (or isn't) healthy."""

    plugin_id: str
    binary_names: list[str]
    custom_executable_path: str | None
    resolved_path: str | None
    detection_method: str
    version_command: list[str] | None
    raw_version_output: str | None
    detected_version: str | None
    health_status: PluginHealthStatus
    health_message: str | None
    checked_at: datetime
