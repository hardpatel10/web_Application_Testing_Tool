"""Scan Profile schema: profiles are DATA, never code.

A :class:`ScanProfile` describes *what* to scan — never a literal Nmap
command string. ``command_builder.py`` is the only place a profile is ever
turned into an actual argv, so no Nmap flag for a specific profile is
ever hardcoded anywhere outside a profile's own JSON file (see
``profiles/*.json``).
"""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from backend.models.enums import TargetType

_ID_PATTERN_MESSAGE = "id must start with a lowercase letter and contain only lowercase letters, digits, or underscores."


class ProfileCategory(StrEnum):
    """Built-in taxonomy a Scan Profile is grouped under, for the profile browser UI."""

    NETWORK_DISCOVERY = "network_discovery"
    TCP = "tcp"
    UDP = "udp"
    WEB = "web"
    SSL_TLS = "ssl_tls"
    SSH = "ssh"
    SMB = "smb"
    SNMP = "snmp"
    RDP = "rdp"
    DNS = "dns"
    DATABASE = "database"
    MAIL = "mail"
    REMOTE_ACCESS = "remote_access"
    GENERAL_ENUMERATION = "general_enumeration"


class RiskLevel(StrEnum):
    """How intrusive/disruptive running this profile against a target is likely to be."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScanProfile(BaseModel):
    """One reusable, named Nmap scan definition, loaded from a JSON file.

    ``arguments`` covers scan-type flags only (e.g. ``-sS``, ``-sV``,
    ``-O``) — never ports, scripts, or timing, which are their own fields
    so ``command_builder.py`` can apply user overrides (``AdvancedOptions``)
    to exactly one of them without needing to parse or rewrite raw flag
    strings.
    """

    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    category: ProfileCategory
    icon: str = Field(default="radar", max_length=50)
    supported_targets: list[TargetType] = Field(min_length=1)
    arguments: list[str] = Field(default_factory=list, description="Scan-type flags this profile always applies.")
    required_ports: str | None = Field(
        default=None, description="Nmap -p syntax (e.g. '1-65535', '445', '1-1000,8080'). None uses Nmap's own default."
    )
    required_scripts: list[str] = Field(default_factory=list, description="NSE script names/categories for --script.")
    script_args: dict[str, str] = Field(default_factory=dict, description="Baked-in --script-args for this profile.")
    minimum_tool_version: str | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    estimated_duration: str = Field(default="1-5 minutes", max_length=50)
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
    """User overrides layered on top of a profile's own arguments for one specific job.

    Every field is optional; an unset field falls back to the profile's
    own value (or Nmap's own default) unchanged.
    """

    timing: int | None = Field(default=None, ge=0, le=5, description="Nmap -T0 (paranoid) through -T5 (insane).")
    retries: int | None = Field(default=None, ge=0, description="--max-retries; overrides the tool's configured default.")
    port_range: str | None = Field(default=None, description="Nmap -p syntax; overrides the profile's required_ports.")
    top_ports: int | None = Field(default=None, gt=0, description="--top-ports N; ignored if port_range is also set.")
    verbosity: int | None = Field(default=None, ge=0, le=3, description="Number of -v flags.")
    additional_arguments: list[str] = Field(default_factory=list, description="Raw flags appended after everything else.")
    script_args: dict[str, str] = Field(default_factory=dict, description="Merged with the profile's own script_args.")
