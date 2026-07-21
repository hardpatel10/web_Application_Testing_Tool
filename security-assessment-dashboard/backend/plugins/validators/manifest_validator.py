"""Validates a plugin's ``plugin.json`` against the manifest schema.

Parsing/field-level validation is owned entirely by
:class:`~backend.plugins.models.manifest.PluginManifest` (a Pydantic
model) so there is exactly one definition of "what makes a manifest
valid" — this module's job is only to run that model and translate its
exception into the framework's shared :class:`PluginValidationResult`
shape, plus the JSON-syntax check the model can't perform on its own.
"""

import json
from pathlib import Path

from pydantic import ValidationError

from backend.plugins.models.manifest import PluginManifest
from backend.plugins.models.validation import PluginValidationResult


def validate_manifest_file(manifest_path: Path) -> tuple[PluginManifest | None, PluginValidationResult]:
    """Load and validate ``manifest_path``. Returns ``(manifest_or_None, result)``."""
    try:
        raw_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, PluginValidationResult(valid=False, errors=[f"Could not read '{manifest_path}': {exc}"])

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, PluginValidationResult(valid=False, errors=[f"'{manifest_path.name}' is not valid JSON: {exc}"])

    if not isinstance(data, dict):
        return None, PluginValidationResult(valid=False, errors=[f"'{manifest_path.name}' must contain a JSON object."])

    try:
        manifest = PluginManifest.model_validate(data)
    except ValidationError as exc:
        errors = [f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()]
        return None, PluginValidationResult(valid=False, errors=errors)

    return manifest, PluginValidationResult(valid=True)
