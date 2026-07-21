"""Service layer adapting the plugin framework to the HTTP API.

Translates :mod:`backend.plugins.exceptions` (framework-internal, HTTP
agnostic) into :mod:`backend.core.exceptions` (the app's HTTP error
hierarchy) at this boundary — the same role ``TargetService`` plays for
DB-not-found errors.
"""

from backend.core.exceptions import NotFoundError
from backend.plugins.exceptions import PluginNotFoundError
from backend.plugins.manager.plugin_manager import PluginManager
from backend.plugins.registry.registered_plugin import RegisteredPlugin
from backend.schemas.plugin import (
    PluginConfigurationResponse,
    PluginDetail,
    PluginDiscoveryFailure,
    PluginHealthResponse,
    PluginReloadResponse,
    PluginSummary,
    PluginValidationResponse,
)


class PluginService:
    """Read-only plugin inspection and reload, backed by the in-memory :class:`PluginManager`."""

    def __init__(self, manager: PluginManager) -> None:
        self._manager = manager

    def list_plugins(self) -> list[PluginSummary]:
        return [self._to_summary(registered) for registered in self._manager.list_plugins()]

    def get_plugin(self, plugin_id: str) -> PluginDetail:
        registered = self._get_or_404(plugin_id)
        return self._to_detail(registered)

    def get_health(self, plugin_id: str) -> PluginHealthResponse:
        self._get_or_404(plugin_id)
        health = self._manager.plugin_status(plugin_id)
        return PluginHealthResponse(
            plugin_id=health.plugin_id,
            status=health.status,
            installed=health.installed,
            version_detected=health.version_detected,
            message=health.message,
            checked_at=health.checked_at,
        )

    def validate(self, plugin_id: str) -> PluginValidationResponse:
        self._get_or_404(plugin_id)
        result = self._manager.validate_plugin(plugin_id)
        return PluginValidationResponse(
            plugin_id=plugin_id, valid=result.valid, errors=result.errors, warnings=result.warnings
        )

    def reload(self) -> PluginReloadResponse:
        self._manager.discover_and_register()
        return PluginReloadResponse(
            registered_count=len(self._manager.list_plugins()),
            plugins=[self._to_summary(registered) for registered in self._manager.list_plugins()],
            failures=[
                PluginDiscoveryFailure(directory=str(failure.directory), error=failure.error or "Unknown error.")
                for failure in self._manager.discovery_failures()
            ],
        )

    def _get_or_404(self, plugin_id: str) -> RegisteredPlugin:
        try:
            return self._manager.get_plugin(plugin_id)
        except PluginNotFoundError as exc:
            raise NotFoundError(exc.message) from exc

    def _to_summary(self, registered: RegisteredPlugin) -> PluginSummary:
        metadata = registered.instance.metadata()
        return PluginSummary(
            id=metadata.id,
            display_name=metadata.display_name,
            version=metadata.version,
            author=metadata.author,
            enabled=registered.config.enabled,
            installed=registered.instance.check_installation(),
            validation_valid=registered.validation.valid,
        )

    def _to_detail(self, registered: RegisteredPlugin) -> PluginDetail:
        metadata = registered.instance.metadata()
        config = registered.config
        return PluginDetail(
            id=metadata.id,
            display_name=metadata.display_name,
            version=metadata.version,
            author=metadata.author,
            description=metadata.description,
            homepage=metadata.homepage,
            license=metadata.license,
            supported_platforms=metadata.supported_platforms,
            supported_targets=metadata.supported_targets,
            supported_output_formats=metadata.supported_output_formats,
            required_binaries=metadata.required_binaries,
            documentation_url=metadata.documentation_url,
            dependencies=registered.manifest.dependencies,
            missing_dependencies=self._manager.check_dependencies(metadata.id),
            config=PluginConfigurationResponse(
                enabled=config.enabled,
                default_timeout_seconds=config.default_timeout_seconds,
                working_directory=str(config.working_directory) if config.working_directory else None,
                arguments=config.arguments,
                environment_variables=config.environment_variables,
                temp_directory=str(config.temp_directory) if config.temp_directory else None,
            ),
            validation_valid=registered.validation.valid,
            validation_errors=registered.validation.errors,
            validation_warnings=registered.validation.warnings,
            source_path=str(registered.source_path),
            loaded_at=registered.loaded_at,
        )
