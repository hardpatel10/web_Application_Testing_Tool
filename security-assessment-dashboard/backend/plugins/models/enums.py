"""Enumerations owned by the plugin framework.

``TargetType`` and ``RawOutputFormat`` already exist as plain, DB-agnostic
``StrEnum`` types in :mod:`backend.models.enums` (no SQLAlchemy import in
that module) and are reused here for a plugin manifest's
``supported_targets``/``supported_output_formats`` rather than being
redefined — see ``DECISIONS.md`` ("Plugin manifests reuse the domain
TargetType/RawOutputFormat enums") for why this isn't a layering
violation. Only concepts genuinely new to the plugin framework get an
enum of their own here.
"""

from enum import StrEnum


class SupportedPlatform(StrEnum):
    """Operating system family a plugin declares it can run on."""

    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"


class PluginHealthStatus(StrEnum):
    """Result of a plugin's runtime health check."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    NOT_INSTALLED = "not_installed"
    UNKNOWN = "unknown"
