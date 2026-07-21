"""High-level plugin API used by the rest of the application.

Coordinates the loader (filesystem discovery + import) and the registry
(in-memory bookkeeping) behind the small set of operations the API layer
actually needs. Nothing above this class needs to know that a loader or a
registry exist at all.
"""

from datetime import datetime, timezone
from pathlib import Path

from backend.plugins.exceptions import PluginValidationError
from backend.plugins.loader.discovered_plugin import DiscoveredPlugin
from backend.plugins.loader.plugin_loader import PluginLoader
from backend.plugins.models.health import PluginHealth
from backend.plugins.models.validation import PluginValidationResult
from backend.plugins.registry.plugin_registry import PluginRegistry
from backend.plugins.registry.registered_plugin import RegisteredPlugin
from backend.plugins.validators.plugin_validator import PluginValidator


class PluginManager:
    """Facade over discovery + registration, exposing operations the app needs."""

    def __init__(
        self,
        loader: PluginLoader,
        registry: PluginRegistry | None = None,
        validator: PluginValidator | None = None,
    ) -> None:
        self._loader = loader
        self._registry = registry or PluginRegistry()
        self._validator = validator or PluginValidator()
        self._discovery_failures: list[DiscoveredPlugin] = []
        self._last_discovered_at: datetime | None = None

    def discover_and_register(self) -> None:
        """Re-scan the plugins directory from scratch and repopulate the registry."""
        self._registry.clear()
        self._discovery_failures = []
        self._last_discovered_at = datetime.now(timezone.utc)

        for result in self._loader.discover():
            if not result.success or result.registered is None:
                self._discovery_failures.append(result)
                continue
            try:
                self._registry.register(result.registered)
            except PluginValidationError as exc:
                self._discovery_failures.append(
                    DiscoveredPlugin(directory=result.directory, success=False, manifest=result.manifest, error=exc.message)
                )

    def list_plugins(self) -> list[RegisteredPlugin]:
        return self._registry.list_all()

    def get_plugin(self, plugin_id: str) -> RegisteredPlugin:
        return self._registry.get(plugin_id)

    def installed_plugins(self) -> list[RegisteredPlugin]:
        """Return only the plugins whose ``check_installation()`` reports true."""
        return [registered for registered in self._registry.list_all() if registered.instance.check_installation()]

    def plugin_status(self, plugin_id: str) -> PluginHealth:
        return self._registry.get(plugin_id).instance.health()

    def validate_plugin(self, plugin_id: str) -> PluginValidationResult:
        """Re-run structure/manifest/interface validation for an already-registered plugin."""
        registered = self._registry.get(plugin_id)
        _, result = self._validator.validate_full(registered.source_path, type(registered.instance))
        return result

    def check_dependencies(self, plugin_id: str) -> list[str]:
        """Return the declared dependency ids of ``plugin_id`` that aren't currently registered."""
        return self._registry.check_dependencies(plugin_id)

    def enable_plugin(self, plugin_id: str) -> None:
        self._registry.enable(plugin_id)

    def disable_plugin(self, plugin_id: str) -> None:
        self._registry.disable(plugin_id)

    def reload_plugin(self, plugin_id: str) -> RegisteredPlugin:
        """Re-run full discovery, then return the freshly reloaded plugin.

        A full re-discovery (not a single-directory reload) is used so
        duplicate-id and inter-plugin-dependency invariants are always
        re-checked against the complete, current set of plugin directories.
        """
        self.discover_and_register()
        return self._registry.get(plugin_id)

    def reload_all(self) -> int:
        """Re-run full discovery. Returns the number of successfully registered plugins."""
        self.discover_and_register()
        return len(self._registry.list_all())

    def discovery_failures(self) -> list[DiscoveredPlugin]:
        """Plugin directories that failed to load during the last discovery pass."""
        return list(self._discovery_failures)

    def last_discovered_at(self) -> datetime | None:
        """When ``discover_and_register`` last ran, or ``None`` if it hasn't yet."""
        return self._last_discovered_at


_manager: PluginManager | None = None


def get_plugin_manager(plugins_root: Path) -> PluginManager:
    """Return the process-wide :class:`PluginManager`, discovering plugins on first access.

    Mirrors the module-level singleton pattern already used for the
    database engine (``backend.database.session._engine``) rather than
    ``functools.lru_cache`` on ``Settings``, since this object is mutable
    in-memory state, not a cached pure function of its inputs.
    """
    global _manager
    if _manager is None:
        _manager = PluginManager(PluginLoader(plugins_root))
        _manager.discover_and_register()
    return _manager
