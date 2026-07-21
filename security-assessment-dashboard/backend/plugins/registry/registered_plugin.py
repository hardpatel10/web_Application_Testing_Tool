"""A single entry in the plugin registry."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from backend.plugins.core.base_plugin import BasePlugin
from backend.plugins.models.config import PluginConfiguration
from backend.plugins.models.manifest import PluginManifest
from backend.plugins.models.validation import PluginValidationResult


@dataclass
class RegisteredPlugin:
    """A successfully loaded and registered plugin, plus its bookkeeping.

    A plain dataclass rather than a Pydantic model: it holds a live
    ``BasePlugin`` instance, which is not (and should not be) a
    serializable value object.
    """

    manifest: PluginManifest
    instance: BasePlugin
    source_path: Path
    validation: PluginValidationResult
    loaded_at: datetime
    config: PluginConfiguration = field(default_factory=PluginConfiguration)
