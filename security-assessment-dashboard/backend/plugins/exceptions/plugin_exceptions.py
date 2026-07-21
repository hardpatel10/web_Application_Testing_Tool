"""Plugin framework exception hierarchy.

Deliberately independent of :mod:`backend.core.exceptions` (the FastAPI/HTTP
error hierarchy): ``backend.plugins`` has no dependency on the web layer, so
it raises its own exceptions here. ``backend.services.plugin_service``
catches these at the service boundary and re-raises the equivalent
``backend.core.exceptions.AppException`` subclass — the same
translation-at-the-boundary pattern already used for DB-not-found errors in
``TargetService``/``AssessmentService``.
"""


class PluginError(Exception):
    """Base class for all plugin-framework exceptions."""

    def __init__(self, message: str, *, plugin_id: str | None = None) -> None:
        self.message = message
        self.plugin_id = plugin_id
        super().__init__(message)


class PluginLoadError(PluginError):
    """Raised when a plugin's code fails to import or instantiate."""


class PluginValidationError(PluginError):
    """Raised when a plugin's manifest, directory, or interface is invalid."""


class PluginExecutionError(PluginError):
    """Raised for failures while preparing/running a plugin invocation."""


class PluginConfigurationError(PluginError):
    """Raised when a plugin's configuration is invalid or incomplete."""


class PluginDependencyError(PluginError):
    """Raised when a plugin declares a dependency that cannot be satisfied."""


class PluginNotFoundError(PluginError):
    """Raised when a plugin id has no registered plugin."""
