"""Filesystem discovery and dynamic import of plugins."""

from backend.plugins.loader.discovered_plugin import DiscoveredPlugin
from backend.plugins.loader.plugin_loader import PluginLoader

__all__ = ["DiscoveredPlugin", "PluginLoader"]
