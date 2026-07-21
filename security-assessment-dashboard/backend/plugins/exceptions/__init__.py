"""Structured exceptions for the plugin framework."""

from backend.plugins.exceptions.plugin_exceptions import (
    PluginConfigurationError,
    PluginDependencyError,
    PluginError,
    PluginExecutionError,
    PluginLoadError,
    PluginNotFoundError,
    PluginValidationError,
)

__all__ = [
    "PluginConfigurationError",
    "PluginDependencyError",
    "PluginError",
    "PluginExecutionError",
    "PluginLoadError",
    "PluginNotFoundError",
    "PluginValidationError",
]
