"""Plugin management endpoints.

Read-only inspection plus a manual re-discovery trigger. No endpoint here
executes a plugin or a tool — that capability doesn't exist yet (see
``backend/plugins/README.md``).
"""

from fastapi import APIRouter

from backend.api.dependencies.services import PluginServiceDep
from backend.schemas.plugin import (
    PluginDetail,
    PluginHealthResponse,
    PluginReloadResponse,
    PluginSummary,
    PluginValidationResponse,
)

router = APIRouter(prefix="/plugins", tags=["Plugins"])


@router.get("", response_model=list[PluginSummary], summary="List every discovered plugin")
def list_plugins(service: PluginServiceDep) -> list[PluginSummary]:
    return service.list_plugins()


@router.post("/reload", response_model=PluginReloadResponse, summary="Re-scan the plugins directory")
def reload_plugins(service: PluginServiceDep) -> PluginReloadResponse:
    return service.reload()


@router.get("/{plugin_id}", response_model=PluginDetail, summary="Full detail for one plugin")
def get_plugin(plugin_id: str, service: PluginServiceDep) -> PluginDetail:
    return service.get_plugin(plugin_id)


@router.get("/{plugin_id}/health", response_model=PluginHealthResponse, summary="A plugin's runtime health check")
def get_plugin_health(plugin_id: str, service: PluginServiceDep) -> PluginHealthResponse:
    return service.get_health(plugin_id)


@router.get(
    "/{plugin_id}/validate", response_model=PluginValidationResponse, summary="Re-validate a plugin's structure/manifest/interface"
)
def validate_plugin(plugin_id: str, service: PluginServiceDep) -> PluginValidationResponse:
    return service.validate(plugin_id)
