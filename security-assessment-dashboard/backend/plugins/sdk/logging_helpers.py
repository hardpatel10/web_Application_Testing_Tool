"""Logging helper for plugin authors.

Every plugin logs under the ``plugins.<plugin_id>`` logger namespace, so
log level/handler configuration set up once in ``backend.core.logging``
applies uniformly to every plugin without each one configuring its own
handlers.
"""

import logging


def get_plugin_logger(plugin_id: str) -> logging.Logger:
    """Return the logger a plugin with the given id should use."""
    return logging.getLogger(f"plugins.{plugin_id}")
