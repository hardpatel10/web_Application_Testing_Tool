"""Result of a plugin's runtime health check."""

from datetime import datetime

from pydantic import BaseModel

from backend.plugins.models.enums import PluginHealthStatus


class PluginHealth(BaseModel):
    """A plugin's self-reported installation and readiness status.

    Returned by ``BasePlugin.health()``. Contains only information the
    plugin can determine locally (binary present, version detected) — it
    never reflects tool execution results, since no tool is ever executed
    by the framework itself.
    """

    plugin_id: str
    status: PluginHealthStatus
    installed: bool
    version_detected: str | None = None
    message: str | None = None
    checked_at: datetime
