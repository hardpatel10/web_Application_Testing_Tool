"""Validates that a loaded class actually implements the ``BasePlugin`` contract.

Python's ``ABC``/``abstractmethod`` machinery already refuses to
*instantiate* a subclass with unimplemented abstract methods, raising a
``TypeError`` — this module exists to catch that case earlier and report
it as a normal :class:`PluginValidationResult` with the specific missing
method names, rather than letting an opaque ``TypeError`` propagate out of
the loader.
"""

import inspect

from backend.plugins.core.base_plugin import BasePlugin
from backend.plugins.models.validation import PluginValidationResult


def validate_interface(plugin_class: type) -> PluginValidationResult:
    """Check that ``plugin_class`` is a concrete ``BasePlugin`` subclass."""
    if not (inspect.isclass(plugin_class) and issubclass(plugin_class, BasePlugin)):
        return PluginValidationResult(
            valid=False,
            errors=[f"'{getattr(plugin_class, '__name__', plugin_class)}' does not extend BasePlugin."],
        )

    if inspect.isabstract(plugin_class):
        missing = sorted(plugin_class.__abstractmethods__)
        return PluginValidationResult(
            valid=False,
            errors=[f"'{plugin_class.__name__}' is missing required method(s): {', '.join(missing)}."],
        )

    return PluginValidationResult(valid=True)
