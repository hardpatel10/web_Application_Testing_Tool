"""Request/response schemas for Scan Profile management.

Mirrors ``backend.plugins.plugins.nmap.models.ScanProfile`` field-for-field
— this is the HTTP-facing shape; the plugin's own model is the framework-
agnostic one with zero FastAPI dependency.
"""

from pydantic import BaseModel, Field

from backend.models.enums import TargetType


class ScanProfileRead(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon: str
    supported_targets: list[TargetType]
    arguments: list[str]
    required_ports: str | None
    required_scripts: list[str]
    script_args: dict[str, str]
    minimum_nmap_version: str | None
    risk_level: str
    estimated_duration: str
    built_in: bool


class ScanProfileWrite(BaseModel):
    """Create/update payload for a custom Scan Profile."""

    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    category: str
    icon: str = "radar"
    supported_targets: list[TargetType] = Field(min_length=1)
    arguments: list[str] = Field(default_factory=list)
    required_ports: str | None = None
    required_scripts: list[str] = Field(default_factory=list)
    script_args: dict[str, str] = Field(default_factory=dict)
    minimum_nmap_version: str | None = None
    risk_level: str = "low"
    estimated_duration: str = "1-5 minutes"


class ScanProfileDuplicateRequest(BaseModel):
    new_id: str = Field(min_length=1, max_length=100)
    new_name: str | None = None


class ScanProfileImportRequest(BaseModel):
    """Raw profile data (e.g. a pasted/uploaded exported profile) to import as a new custom profile."""

    profile: dict


class CommandPreviewRequest(BaseModel):
    """Preview the exact argv a profile + target + options would produce, without running anything."""

    profile_id: str
    target_value: str
    advanced_options: dict | None = None


class CommandPreviewResponse(BaseModel):
    command: list[str]
