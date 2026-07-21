"""Facade combining structure, manifest, and interface validation.

Used by :class:`~backend.plugins.loader.plugin_loader.PluginLoader` (fail
closed before registering a plugin) and by
:class:`~backend.plugins.manager.plugin_manager.PluginManager` (report-only
re-validation of an already-registered plugin, for the
``GET /plugins/{id}/validate`` endpoint).
"""

from pathlib import Path

from backend.plugins.models.manifest import PluginManifest
from backend.plugins.models.validation import PluginValidationResult
from backend.plugins.validators.interface_validator import validate_interface
from backend.plugins.validators.manifest_validator import validate_manifest_file
from backend.plugins.validators.structure_validator import validate_structure


class PluginValidator:
    """Runs the three independent validation passes and aggregates results."""

    def validate_structure(self, plugin_directory: Path) -> PluginValidationResult:
        return validate_structure(plugin_directory)

    def validate_manifest(self, plugin_directory: Path) -> tuple[PluginManifest | None, PluginValidationResult]:
        return validate_manifest_file(plugin_directory / "plugin.json")

    def validate_interface(self, plugin_class: type) -> PluginValidationResult:
        return validate_interface(plugin_class)

    def validate_directory(self, plugin_directory: Path) -> tuple[PluginManifest | None, PluginValidationResult]:
        """Filesystem-only checks (structure + manifest); does not import any code."""
        structure_result = self.validate_structure(plugin_directory)
        if not structure_result.valid:
            return None, structure_result

        manifest, manifest_result = self.validate_manifest(plugin_directory)
        return manifest, structure_result.merge(manifest_result)

    def validate_full(
        self, plugin_directory: Path, plugin_class: type | None
    ) -> tuple[PluginManifest | None, PluginValidationResult]:
        """Structure + manifest, plus interface compliance if a class was already imported."""
        manifest, result = self.validate_directory(plugin_directory)
        if plugin_class is not None:
            result = result.merge(self.validate_interface(plugin_class))
        return manifest, result
