"""Plugin SDK: the curated public surface plugin authors import against.

A plugin's ``plugin.py``/``parser.py``/``normalizer.py``/``validator.py``
should only ever need ``from backend.plugins.sdk import ...`` — internal
machinery (``backend.plugins.registry``, ``.loader``, ``.manager``,
``.validators``) is not part of this surface and is not re-exported here.
"""

from backend.plugins.core.base_plugin import BasePlugin
from backend.plugins.exceptions import (
    PluginConfigurationError,
    PluginDependencyError,
    PluginError,
    PluginExecutionError,
    PluginLoadError,
    PluginNotFoundError,
    PluginValidationError,
)
from backend.plugins.models.config import PluginConfiguration
from backend.plugins.models.enums import PluginHealthStatus, SupportedPlatform
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.models.health import PluginHealth
from backend.plugins.models.manifest import PluginManifest
from backend.plugins.models.metadata import PluginMetadata
from backend.plugins.models.normalized import NormalizedHost, NormalizedObservation, NormalizedOutput, NormalizedService
from backend.plugins.sdk.detection_helpers import (
    default_search_directories,
    extract_version,
    find_executable,
    run_version_command,
    validate_custom_executable,
)
from backend.plugins.sdk.detection_plugin import DetectionOnlyPlugin
from backend.plugins.sdk.file_helpers import ensure_directory, read_text_file, write_text_file
from backend.plugins.sdk.json_helpers import parse_json_lines, safe_json_dumps, safe_json_loads
from backend.plugins.sdk.logging_helpers import get_plugin_logger
from backend.plugins.sdk.process_runner import ProcessResult, run_subprocess, terminate_process
from backend.plugins.sdk.temp_helpers import plugin_temp_directory
from backend.plugins.sdk.validators import (
    detect_target_type,
    is_valid_target,
    normalize_target,
)
from backend.plugins.sdk.xml_helpers import safe_xml_parse

__all__ = [
    "BasePlugin",
    "DetectionOnlyPlugin",
    "PluginConfiguration",
    "PluginConfigurationError",
    "PluginDependencyError",
    "PluginError",
    "PluginExecutionContext",
    "PluginExecutionError",
    "PluginHealth",
    "PluginHealthStatus",
    "NormalizedHost",
    "NormalizedObservation",
    "NormalizedOutput",
    "NormalizedService",
    "PluginLoadError",
    "PluginManifest",
    "PluginMetadata",
    "PluginNotFoundError",
    "PluginRawOutput",
    "PluginValidationError",
    "ProcessResult",
    "SupportedPlatform",
    "default_search_directories",
    "detect_target_type",
    "ensure_directory",
    "extract_version",
    "find_executable",
    "get_plugin_logger",
    "is_valid_target",
    "normalize_target",
    "parse_json_lines",
    "plugin_temp_directory",
    "read_text_file",
    "run_subprocess",
    "run_version_command",
    "safe_json_dumps",
    "safe_json_loads",
    "safe_xml_parse",
    "terminate_process",
    "validate_custom_executable",
    "write_text_file",
]
