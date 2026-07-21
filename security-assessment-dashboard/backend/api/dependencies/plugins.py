"""Dependency providers for the process-wide plugin and execution managers."""

from typing import Annotated

from fastapi import Depends

from backend.api.dependencies.config import SettingsDep
from backend.plugins.manager.plugin_manager import PluginManager, get_plugin_manager
from backend.workers.manager import ExecutionManager, get_execution_manager


def get_plugin_manager_dependency(settings: SettingsDep) -> PluginManager:
    return get_plugin_manager(settings.plugins_dir)


PluginManagerDep = Annotated[PluginManager, Depends(get_plugin_manager_dependency)]


def get_execution_manager_dependency(settings: SettingsDep, plugin_manager: PluginManagerDep) -> ExecutionManager:
    return get_execution_manager(settings, plugin_manager)


ExecutionManagerDep = Annotated[ExecutionManager, Depends(get_execution_manager_dependency)]
