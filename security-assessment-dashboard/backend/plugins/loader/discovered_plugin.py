"""Outcome of one directory-load attempt."""

from dataclasses import dataclass
from pathlib import Path

from backend.plugins.models.manifest import PluginManifest
from backend.plugins.models.validation import PluginValidationResult
from backend.plugins.registry.registered_plugin import RegisteredPlugin


@dataclass
class DiscoveredPlugin:
    """Result of :meth:`PluginLoader.discover` attempting to load one directory.

    ``success=False`` carries ``error`` (a human-readable message) instead
    of raising, so the loader can report a broken plugin and keep scanning
    the rest of ``plugins/`` ("ignore invalid plugins" / "produce useful
    error messages").
    """

    directory: Path
    success: bool
    registered: RegisteredPlugin | None = None
    manifest: PluginManifest | None = None
    validation: PluginValidationResult | None = None
    error: str | None = None
