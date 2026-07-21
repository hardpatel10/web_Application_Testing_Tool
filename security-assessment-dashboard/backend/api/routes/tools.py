"""Tool Management endpoints.

Discovers, validates, configures, and monitors the platform's supported
security tools. No endpoint here executes a tool — that capability
doesn't exist yet (see ``backend/plugins/README.md``).
"""

from fastapi import APIRouter, Query

from backend.api.dependencies.services import ToolServiceDep
from backend.models.enums import ToolHealthStatus, ToolStatus
from backend.schemas.tool import (
    FilesystemBrowseResponse,
    ToolConfigurationUpdate,
    ToolDetail,
    ToolDiagnostics,
    ToolDiscoveryResponse,
    ToolHealthResponse,
    ToolSummary,
    ToolValidateRequest,
    ToolValidationResult,
)

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("", response_model=list[ToolSummary], summary="List supported tools and their current status")
async def list_tools(
    service: ToolServiceDep,
    search: str | None = Query(default=None, description="Matches against name or display name."),
    status_filter: ToolStatus | None = Query(default=None, alias="status"),
    health_filter: ToolHealthStatus | None = Query(default=None, alias="health"),
    sort_by: str = Query(default="name"),
    sort_desc: bool = Query(default=False),
) -> list[ToolSummary]:
    return await service.list_tools(
        search=search, status_filter=status_filter, health_filter=health_filter, sort_by=sort_by, sort_desc=sort_desc
    )


@router.get("/browse-filesystem", response_model=FilesystemBrowseResponse, summary="List a directory (for the wordlist/path picker)")
def browse_filesystem(
    service: ToolServiceDep, path: str | None = Query(default=None, description="Defaults to the user's home directory.")
) -> FilesystemBrowseResponse:
    return service.browse_filesystem(path)


@router.post("/discover", response_model=ToolDiscoveryResponse, summary="Re-scan and re-detect every supported tool")
async def discover_tools(service: ToolServiceDep) -> ToolDiscoveryResponse:
    return await service.discover()


@router.post("/validate", response_model=list[ToolValidationResult], summary="Validate one tool (or every tool, if none specified)")
async def validate_tools(payload: ToolValidateRequest, service: ToolServiceDep) -> list[ToolValidationResult]:
    return await service.validate_tools(payload.name)


@router.get("/{name}", response_model=ToolDetail, summary="Full detail for one tool")
async def get_tool(name: str, service: ToolServiceDep) -> ToolDetail:
    return await service.get_tool(name)


@router.get("/{name}/diagnostics", response_model=ToolDiagnostics, summary="Detection/version/health diagnostics for one tool")
async def get_tool_diagnostics(name: str, service: ToolServiceDep) -> ToolDiagnostics:
    return await service.get_diagnostics(name)


@router.post("/{name}/health", response_model=ToolHealthResponse, summary="Run a fresh health check for one tool")
async def check_tool_health(name: str, service: ToolServiceDep) -> ToolHealthResponse:
    return await service.get_health(name)


@router.post("/{name}/refresh", response_model=ToolDetail, summary="Re-run detection/version/health for one tool")
async def refresh_tool(name: str, service: ToolServiceDep) -> ToolDetail:
    return await service.refresh_tool(name)


@router.post("/{name}/validate", response_model=ToolValidationResult, summary="Validate one tool by name")
async def validate_tool(name: str, service: ToolServiceDep) -> ToolValidationResult:
    return (await service.validate_tools(name))[0]


@router.put("/{name}/configuration", response_model=ToolDetail, summary="Update one tool's configuration")
async def update_tool_configuration(name: str, payload: ToolConfigurationUpdate, service: ToolServiceDep) -> ToolDetail:
    return await service.update_configuration(name, payload)
