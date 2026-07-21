"""High-level facade over plugin discovery, registration, and lookup."""

from backend.plugins.manager.plugin_manager import PluginManager, get_plugin_manager

__all__ = ["PluginManager", "get_plugin_manager"]
