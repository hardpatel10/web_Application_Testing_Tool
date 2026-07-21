"""Framework-level plugin validation.

Distinct from :mod:`backend.plugins.sdk.validators` (which validates
*targets* for plugin authors) — this package validates *plugins
themselves*: their manifest, on-disk directory structure, and interface
compliance. Used by the loader (fail-closed, before registration) and by
the ``GET /plugins/{id}/validate`` endpoint (report-only, on demand).
"""

from backend.plugins.validators.plugin_validator import PluginValidator

__all__ = ["PluginValidator"]
