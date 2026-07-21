"""Scan Profile management endpoints.

Nested under a tool (``/tools/{tool_name}/profiles``) since a profile only
ever means something in the context of one specific plugin's command
builder. Only Nmap implements a profile system today; ``GET`` (list/get)
handles that gracefully (empty list / 404), every mutating endpoint
(including enable/disable) 422s with a clear message for such a tool.
"""

from fastapi import APIRouter, Query, status

from backend.api.dependencies.services import ScanProfileServiceDep, ToolServiceDep
from backend.schemas.scan_profile import (
    CommandPreviewRequest,
    CommandPreviewResponse,
    ScanProfileDuplicateRequest,
    ScanProfileImportRequest,
    ScanProfileRead,
    ScanProfileWrite,
)

router = APIRouter(prefix="/tools/{tool_name}/profiles", tags=["Scan Profiles"])


@router.get("", response_model=list[ScanProfileRead], summary="List/search a tool's Scan Profiles")
def list_profiles(
    tool_name: str,
    service: ScanProfileServiceDep,
    query: str | None = Query(default=None, description="Matches against name or description."),
    category: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
) -> list[ScanProfileRead]:
    return service.list_profiles(tool_name, query=query, category=category, risk_level=risk_level)


@router.post("", response_model=ScanProfileRead, status_code=status.HTTP_201_CREATED, summary="Create a custom Scan Profile")
def create_profile(tool_name: str, payload: ScanProfileWrite, service: ScanProfileServiceDep) -> ScanProfileRead:
    return service.create_profile(tool_name, payload)


@router.post("/import", response_model=ScanProfileRead, status_code=status.HTTP_201_CREATED, summary="Import a Scan Profile from raw JSON data")
def import_profile(tool_name: str, payload: ScanProfileImportRequest, service: ScanProfileServiceDep) -> ScanProfileRead:
    return service.import_profile(tool_name, payload)


@router.post("/preview-command", response_model=CommandPreviewResponse, summary="Preview the command a profile + target + options would generate")
def preview_command(tool_name: str, payload: CommandPreviewRequest, service: ScanProfileServiceDep) -> CommandPreviewResponse:
    return service.preview_command(tool_name, payload)


@router.get("/{profile_id}", response_model=ScanProfileRead, summary="Get one Scan Profile")
def get_profile(tool_name: str, profile_id: str, service: ScanProfileServiceDep) -> ScanProfileRead:
    return service.get_profile(tool_name, profile_id)


@router.get("/{profile_id}/export", summary="Export one Scan Profile as raw JSON data")
def export_profile(tool_name: str, profile_id: str, service: ScanProfileServiceDep) -> dict:
    return service.export_profile(tool_name, profile_id)


@router.put("/{profile_id}", response_model=ScanProfileRead, summary="Update a custom Scan Profile (built-in profiles cannot be edited)")
def update_profile(tool_name: str, profile_id: str, payload: ScanProfileWrite, service: ScanProfileServiceDep) -> ScanProfileRead:
    return service.update_profile(tool_name, profile_id, payload)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a custom Scan Profile (built-in profiles cannot be deleted)")
def delete_profile(tool_name: str, profile_id: str, service: ScanProfileServiceDep) -> None:
    service.delete_profile(tool_name, profile_id)


@router.post("/{profile_id}/duplicate", response_model=ScanProfileRead, status_code=status.HTTP_201_CREATED, summary="Duplicate a profile into a new, editable custom profile")
def duplicate_profile(
    tool_name: str, profile_id: str, payload: ScanProfileDuplicateRequest, service: ScanProfileServiceDep
) -> ScanProfileRead:
    return service.duplicate_profile(tool_name, profile_id, payload)


@router.post("/{profile_id}/enable", response_model=ScanProfileRead, summary="Offer a profile for new scans again")
async def enable_profile(
    tool_name: str, profile_id: str, profiles: ScanProfileServiceDep, tools: ToolServiceDep
) -> ScanProfileRead:
    profiles.get_profile(tool_name, profile_id)  # 404s cleanly if unknown, before persisting anything
    await tools.set_profile_enabled(tool_name, profile_id, enabled=True)
    return profiles.get_profile(tool_name, profile_id)


@router.post("/{profile_id}/disable", response_model=ScanProfileRead, summary="Stop offering a profile for new scans (it is not deleted)")
async def disable_profile(
    tool_name: str, profile_id: str, profiles: ScanProfileServiceDep, tools: ToolServiceDep
) -> ScanProfileRead:
    profiles.get_profile(tool_name, profile_id)
    await tools.set_profile_enabled(tool_name, profile_id, enabled=False)
    return profiles.get_profile(tool_name, profile_id)
