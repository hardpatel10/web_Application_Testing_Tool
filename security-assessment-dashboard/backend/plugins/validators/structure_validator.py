"""Validates that a plugin's directory contains the required layout.

Every plugin must follow::

    plugin_name/
        plugin.json
        plugin.py
        parser.py
        normalizer.py
        validator.py
        README.md
"""

from pathlib import Path

from backend.plugins.models.validation import PluginValidationResult

REQUIRED_FILES: tuple[str, ...] = (
    "plugin.json",
    "plugin.py",
    "parser.py",
    "normalizer.py",
    "validator.py",
    "README.md",
)


def validate_structure(plugin_directory: Path) -> PluginValidationResult:
    """Check that ``plugin_directory`` contains every required file."""
    if not plugin_directory.is_dir():
        return PluginValidationResult(valid=False, errors=[f"'{plugin_directory}' is not a directory."])

    errors = [
        f"Missing required file '{file_name}'."
        for file_name in REQUIRED_FILES
        if not (plugin_directory / file_name).is_file()
    ]
    return PluginValidationResult(valid=not errors, errors=errors)
