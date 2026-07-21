"""In-memory store of currently loaded plugins.

Pure bookkeeping: this class never touches the filesystem or imports code
(that is :class:`~backend.plugins.loader.plugin_loader.PluginLoader`'s
job) and never talks to the database (plugins never do, per
``.claude/CLAUDE.md``). It only enforces registry-level invariants —
unique ids, enabled/disabled state, and inter-plugin dependency
resolution.
"""

from backend.plugins.exceptions import PluginNotFoundError, PluginValidationError
from backend.plugins.registry.registered_plugin import RegisteredPlugin


class PluginRegistry:
    """Enforces uniqueness and provides lookup over the set of loaded plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, RegisteredPlugin] = {}

    def register(self, registered: RegisteredPlugin) -> None:
        """Add a plugin to the registry. Raises if its id is already registered."""
        plugin_id = registered.manifest.id
        if plugin_id in self._plugins:
            raise PluginValidationError(f"Duplicate plugin id: '{plugin_id}' is already registered.", plugin_id=plugin_id)
        self._plugins[plugin_id] = registered

    def unregister(self, plugin_id: str) -> None:
        """Remove a plugin from the registry. No-op if it isn't registered."""
        self._plugins.pop(plugin_id, None)

    def clear(self) -> None:
        """Remove every registered plugin (used before a full re-discovery)."""
        self._plugins.clear()

    def get(self, plugin_id: str) -> RegisteredPlugin:
        """Return the registered plugin with the given id, or raise ``PluginNotFoundError``."""
        try:
            return self._plugins[plugin_id]
        except KeyError:
            raise PluginNotFoundError(f"No plugin registered with id '{plugin_id}'.", plugin_id=plugin_id) from None

    def list_all(self) -> list[RegisteredPlugin]:
        """Return every registered plugin, sorted by id for stable ordering."""
        return [self._plugins[plugin_id] for plugin_id in sorted(self._plugins)]

    def enable(self, plugin_id: str) -> None:
        self.get(plugin_id).config.enabled = True

    def disable(self, plugin_id: str) -> None:
        self.get(plugin_id).config.enabled = False

    def is_enabled(self, plugin_id: str) -> bool:
        return self.get(plugin_id).config.enabled

    def check_dependencies(self, plugin_id: str) -> list[str]:
        """Return the declared dependency ids of ``plugin_id`` that are not currently registered."""
        registered = self.get(plugin_id)
        return [dependency_id for dependency_id in registered.manifest.dependencies if dependency_id not in self._plugins]
