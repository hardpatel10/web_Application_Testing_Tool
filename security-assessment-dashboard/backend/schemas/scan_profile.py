"""Request/response schemas for Scan Profile management.

A superset of every tool's own ``ScanProfile`` fields: this is the one
HTTP-facing shape shared by every plugin with a profile system (Nmap,
Nikto, Nuclei, SSLScan so far), so each plugin's own field set (e.g.
Nmap's ``required_ports``/``required_scripts``, Nikto's ``tuning``/
``plugins``, Nuclei's ``templates``/``tags``/``severities``, SSLScan's
``connect_timeout_seconds``) is represented here as an optional field
that stays ``None``/empty for a tool whose own model doesn't have it.
``ScanProfileService._to_read`` reads each field via ``getattr`` with a
default rather than direct attribute access for exactly this reason --
the object handed in is one specific plugin's own ``ScanProfile``
instance, not this shared shape.

Adding another profile-supporting plugin with genuinely new tunable
dimensions means adding new optional fields here, never touching what
already exists for the others.
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
    minimum_tool_version: str | None
    risk_level: str
    estimated_duration: str
    built_in: bool
    enabled: bool

    # Nmap-specific
    required_ports: str | None = None
    required_scripts: list[str] = Field(default_factory=list)
    script_args: dict[str, str] = Field(default_factory=dict)

    # Nikto-specific
    tuning: str | None = None
    plugins: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = None

    # Nuclei-specific
    templates: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    exclude_tags: list[str] = Field(default_factory=list)
    severities: list[str] = Field(default_factory=list)

    # SSLScan-specific
    connect_timeout_seconds: int | None = None


class ScanProfileWrite(BaseModel):
    """Create/update payload for a custom Scan Profile.

    Only the fields relevant to the target tool need to be supplied --
    each plugin's own ``ProfileManager`` validates the resulting dict
    against its own ``ScanProfile`` model, which silently ignores fields
    it doesn't define (Pydantic's default "extra=ignore" behavior).
    """

    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    category: str
    icon: str = "radar"
    supported_targets: list[TargetType] = Field(min_length=1)
    arguments: list[str] = Field(default_factory=list)
    minimum_tool_version: str | None = None
    risk_level: str = "low"
    estimated_duration: str = "1-5 minutes"

    # Nmap-specific
    required_ports: str | None = None
    required_scripts: list[str] = Field(default_factory=list)
    script_args: dict[str, str] = Field(default_factory=dict)

    # Nikto-specific
    tuning: str | None = None
    plugins: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = None

    # Nuclei-specific
    templates: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    exclude_tags: list[str] = Field(default_factory=list)
    severities: list[str] = Field(default_factory=list)

    # SSLScan-specific
    connect_timeout_seconds: int | None = None


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
