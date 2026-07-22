"""Scan Profile schema: profiles are DATA, never code.

A :class:`ScanProfile` describes *what* to test -- never a literal SSLScan
command string. ``command_builder.py`` is the only place a profile is ever
turned into an actual argv, so no SSLScan flag for a specific profile is
ever hardcoded anywhere outside a profile's own JSON file (see
``profiles/*.json``). Mirrors ``backend.plugins.plugins.nikto.models``/
``backend.plugins.plugins.nuclei.models`` field-for-field where the concept
is the same (id/name/description/category/risk_level/estimated_duration/
built_in); ``timeout_seconds``/``connect_timeout_seconds`` map onto
SSLScan's own ``--timeout``/``--connect-timeout``.
"""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from backend.models.enums import TargetType

_ID_PATTERN_MESSAGE = "id must start with a lowercase letter and contain only lowercase letters, digits, or underscores."


class ProfileCategory(StrEnum):
    """Built-in taxonomy a Scan Profile is grouped under, for the profile browser UI."""

    DEFAULT = "default"
    DEEP = "deep"
    CERTIFICATE = "certificate"
    PROTOCOL = "protocol"
    CIPHER = "cipher"
    CUSTOM = "custom"


class RiskLevel(StrEnum):
    """How intrusive/disruptive running this profile against a target is likely to be."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScanProfile(BaseModel):
    """One reusable, named SSLScan scan definition, loaded from a JSON file."""

    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    category: ProfileCategory
    icon: str = Field(default="lock", max_length=50)
    supported_targets: list[TargetType] = Field(min_length=1)
    arguments: list[str] = Field(default_factory=list, description="Fixed flags this profile always applies.")
    timeout_seconds: int | None = Field(
        default=None, gt=0, description="SSLScan's own --timeout (per-socket read timeout), not the job timeout."
    )
    connect_timeout_seconds: int | None = Field(default=None, gt=0, description="SSLScan's own --connect-timeout.")
    minimum_tool_version: str | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    estimated_duration: str = Field(default="1-3 minutes", max_length=50)
    built_in: bool = True

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if not value or not value[0].isalpha() or not value.islower():
            raise ValueError(_ID_PATTERN_MESSAGE)
        if not all(c.islower() or c.isdigit() or c == "_" for c in value):
            raise ValueError(_ID_PATTERN_MESSAGE)
        return value


class AdvancedOptions(BaseModel):
    """User overrides layered on top of a profile's own settings for one specific job.

    Every field is optional; an unset field falls back to the profile's
    own value (or SSLScan's own default) unchanged.
    """

    sni_name: str | None = Field(default=None, max_length=255, description="Overrides SNI hostname (--sni-name).")
    ip_version: str | None = Field(default=None, description="'4' or '6' to force --ipv4/--ipv6.")
    port: int | None = Field(default=None, gt=0, le=65535, description="Overrides the resolved target's port.")
    timeout_seconds: int | None = Field(default=None, gt=0, description="Overrides the profile's --timeout.")
    connect_timeout_seconds: int | None = Field(default=None, gt=0, description="Overrides the profile's --connect-timeout.")
    additional_arguments: list[str] = Field(default_factory=list, description="Raw flags appended after everything else.")

    @field_validator("ip_version")
    @classmethod
    def _validate_ip_version(cls, value: str | None) -> str | None:
        if value is not None and value not in ("4", "6"):
            raise ValueError("ip_version must be '4' or '6'.")
        return value
