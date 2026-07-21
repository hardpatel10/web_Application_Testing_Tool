"""Discovers, validates, imports, and instantiates plugins from disk.

Every plugin directory under the configured plugins root is loaded
independently. A plugin that fails structure/manifest/interface
validation, fails to import, or fails to instantiate is recorded as a
failed :class:`DiscoveredPlugin` with a specific error message — it never
aborts discovery of the remaining plugins.

Each plugin directory is loaded as its own synthetic Python *package*
(built via ``importlib.util.spec_from_file_location`` +
``ModuleSpec.submodule_search_locations``, not real ``__init__.py``
files), so a plugin's ``plugin.py`` can use ordinary relative imports
(``from .parser import parse_output``) to reach its sibling
``parser.py``/``normalizer.py``/``validator.py`` modules. This works no
matter where ``plugins_root`` actually points on disk — unlike importing
plugins as real submodules of ``backend.plugins.plugins`` (Python's import
system can only resolve those to whatever directory is on that package's
own ``__path__``), so ``Settings.plugins_dir`` genuinely stays
configurable, not just nominally so.
"""

import importlib.machinery
import importlib.util
import inspect
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

from backend.plugins.core.base_plugin import BasePlugin
from backend.plugins.exceptions import PluginLoadError
from backend.plugins.loader.discovered_plugin import DiscoveredPlugin
from backend.plugins.models.config import PluginConfiguration
from backend.plugins.registry.registered_plugin import RegisteredPlugin
from backend.plugins.utils.plugin_paths import entrypoint_module_path, split_entrypoint
from backend.plugins.validators.plugin_validator import PluginValidator


class PluginLoader:
    """Scans a directory of plugin subdirectories and loads each one."""

    def __init__(self, plugins_root: Path, validator: PluginValidator | None = None) -> None:
        self._plugins_root = plugins_root
        self._validator = validator or PluginValidator()
        # Tracks the synthetic package name most recently used for each
        # plugin directory, so a later reload can purge exactly that
        # directory's stale sys.modules entries instead of leaking a fresh
        # set of module objects on every reload.
        self._package_names_by_directory: dict[Path, str] = {}

    def discover(self) -> list[DiscoveredPlugin]:
        """Attempt to load every immediate subdirectory of the plugins root.

        Never raises. Returns one :class:`DiscoveredPlugin` per candidate
        directory found (dotfiles/``__pycache__``-style directories are
        skipped silently, not reported as failures).
        """
        if not self._plugins_root.is_dir():
            return []

        return [
            self._load_one(entry)
            for entry in sorted(self._plugins_root.iterdir())
            if entry.is_dir() and not entry.name.startswith((".", "_"))
        ]

    def _load_one(self, plugin_directory: Path) -> DiscoveredPlugin:
        manifest, validation = self._validator.validate_directory(plugin_directory)
        if manifest is None:
            return DiscoveredPlugin(
                directory=plugin_directory,
                success=False,
                validation=validation,
                error="; ".join(validation.errors) or "Manifest/structure validation failed.",
            )

        try:
            plugin_class = self._import_entrypoint(plugin_directory, manifest.entrypoint)
        except PluginLoadError as exc:
            return DiscoveredPlugin(directory=plugin_directory, success=False, manifest=manifest, error=exc.message)

        _, full_validation = self._validator.validate_full(plugin_directory, plugin_class)
        if not full_validation.valid:
            return DiscoveredPlugin(
                directory=plugin_directory,
                success=False,
                manifest=manifest,
                validation=full_validation,
                error="; ".join(full_validation.errors),
            )

        # The same PluginConfiguration instance is shared between the plugin
        # object and its RegisteredPlugin wrapper (not two independent
        # defaults) so that mutating registered.config (e.g. from
        # ToolService.update_configuration) is immediately visible to the
        # running plugin's own self._config, and vice versa.
        config = PluginConfiguration()
        try:
            instance = plugin_class(manifest, config)
        except Exception as exc:  # noqa: BLE001 - a misbehaving plugin constructor must not crash the app
            return DiscoveredPlugin(
                directory=plugin_directory,
                success=False,
                manifest=manifest,
                error=f"Failed to instantiate '{plugin_class.__name__}': {exc}",
            )

        registered = RegisteredPlugin(
            manifest=manifest,
            instance=instance,
            source_path=plugin_directory,
            validation=full_validation,
            loaded_at=datetime.now(timezone.utc),
            config=config,
        )
        return DiscoveredPlugin(
            directory=plugin_directory, success=True, registered=registered, manifest=manifest, validation=full_validation
        )

    def _import_entrypoint(self, plugin_directory: Path, entrypoint: str) -> type[BasePlugin]:
        module_stem, class_name = split_entrypoint(entrypoint)
        module_path = entrypoint_module_path(plugin_directory, entrypoint)
        if not module_path.is_file():
            raise PluginLoadError(f"Entrypoint module '{module_stem}.py' not found in '{plugin_directory}'.")

        self._purge_stale_modules(plugin_directory)
        package_name = f"_plugin_{plugin_directory.name}_{uuid.uuid4().hex}"
        self._package_names_by_directory[plugin_directory] = package_name

        self._register_synthetic_package(package_name, plugin_directory)
        module_name = f"{package_name}.{module_stem}"

        try:
            module = self._exec_module(module_name, module_path, package_name)
        except Exception as exc:  # noqa: BLE001 - any import-time error is a load failure, not a framework crash
            raise PluginLoadError(f"Error importing '{module_stem}.py': {exc}") from exc

        plugin_class = getattr(module, class_name, None)
        if plugin_class is None:
            raise PluginLoadError(f"'{module_stem}.py' has no attribute '{class_name}'.")
        if not inspect.isclass(plugin_class):
            raise PluginLoadError(f"'{class_name}' in '{module_stem}.py' is not a class.")
        return plugin_class

    def _purge_stale_modules(self, plugin_directory: Path) -> None:
        """Drop the previous load's synthetic package/submodules for this directory, if any."""
        previous_package_name = self._package_names_by_directory.pop(plugin_directory, None)
        if previous_package_name is None:
            return
        for cached_name in [
            name for name in sys.modules if name == previous_package_name or name.startswith(f"{previous_package_name}.")
        ]:
            del sys.modules[cached_name]

    @staticmethod
    def _register_synthetic_package(package_name: str, plugin_directory: Path) -> None:
        """Register a namespace-style package in ``sys.modules`` rooted at ``plugin_directory``.

        Lets the entrypoint module's relative imports (``from .parser import
        ...``) resolve sibling files in the same directory, without those
        files needing a real ``__init__.py`` or living under any particular
        fixed path.
        """
        spec = importlib.machinery.ModuleSpec(package_name, loader=None, is_package=True)
        spec.submodule_search_locations = [str(plugin_directory)]
        package_module = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = package_module

    @staticmethod
    def _exec_module(module_name: str, module_path: Path, package_name: str) -> ModuleType:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Could not create an import spec for '{module_path}'.")

        module = importlib.util.module_from_spec(spec)
        module.__package__ = package_name
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            del sys.modules[module_name]
            raise
        return module
