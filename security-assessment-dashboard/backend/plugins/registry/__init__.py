"""In-memory plugin registry."""

from backend.plugins.registry.plugin_registry import PluginRegistry
from backend.plugins.registry.registered_plugin import RegisteredPlugin

__all__ = ["PluginRegistry", "RegisteredPlugin"]
