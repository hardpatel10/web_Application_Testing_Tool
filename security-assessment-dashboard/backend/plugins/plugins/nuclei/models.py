"""Scan Profile schema: profiles are DATA, never code.

A :class:`ScanProfile` describes *what* to scan — never a literal Nuclei
command string. ``command_builder.py`` is the only place a profile is ever
turned into an actual argv, so no Nuclei flag for a specific profile is
ever hardcoded anywhere outside a profile's own JSON file (see
``profiles/*.json``). Mirrors ``backend.plugins.plugins.nmap.models``
field-for-field where the concept is the same (id/name/description/
category/risk_level/estimated_duration/built_in); ``templates``/``tags``/
``exclude_tags``/``severities`` replace Nmap's ports/scripts since those
are Nuclei's own tunable dimensions.
"""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from backend.models.enums import TargetType

_ID_PATTERN_MESSAGE = "id must start with a lowercase letter and contain only lowercase letters, digits, or underscores."


class ProfileCategory(StrEnum):
    """Built-in taxonomy a Scan Profile is grouped under, for the profile browser UI."""

    QUICK = "quick"
    DEFAULT = "default"
    WEB = "web"
    SSL = "ssl"
    EXPOSURE = "exposure"
    CVE = "cve"
    MISCONFIGURATION = "misconfiguration"
    TECHNOLOGY = "technology"
    CUSTOM = "custom"


class RiskLevel(StrEnum):
    """How intrusive/disruptive running this profile against a target is likely to be."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScanProfile(BaseModel):
    """One reusable, named Nuclei scan definition, loaded from a JSON file.

    ``templates``/``tags``/``exclude_tags``/``severities`` are Nuclei's own
    ``-t``/``-tags``/``-etags``/``-severity`` selectors; ``arguments``
    covers any other fixed flag a profile always applies.
    """

    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    category: ProfileCategory
    icon: str = Field(default="scan-search", max_length=50)
    supported_targets: list[TargetType] = Field(min_length=1)
    arguments: list[str] = Field(default_factory=list, description="Fixed flags this profile always applies.")
    templates: list[str] = Field(default_factory=list, description="Nuclei -t template paths/directories, e.g. ['cves/'].")
    tags: list[str] = Field(default_factory=list, description="Nuclei -tags to include, e.g. ['exposure','misconfig'].")
    exclude_tags: list[str] = Field(default_factory=list, description="Nuclei -etags to exclude.")
    severities: list[str] = Field(
        default_factory=list, description="Nuclei -severity filter, e.g. ['critical','high']. Empty means no filter."
    )
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
    """User overrides layered on top of a profile's own settings for one specific job.

    Every field is optional; an unset field falls back to the profile's
    own value (or Nuclei's own default) unchanged. Rate limit/concurrency/
    retries fall back to the tool's own configured defaults
    (``PluginConfiguration.rate_limit``/``.retries``) when neither the
    profile nor these overrides set them, exactly like Nmap's
    ``default_rate_limit``/``default_retries`` parameters.
    """

    templates: list[str] | None = Field(default=None, description="Overrides the profile's -t templates.")
    tags: list[str] | None = Field(default=None, description="Overrides the profile's -tags.")
    exclude_tags: list[str] | None = Field(default=None, description="Overrides the profile's -etags.")
    severities: list[str] | None = Field(default=None, description="Overrides the profile's -severity filter.")
    rate_limit: int | None = Field(default=None, gt=0, description="-rl; overrides the tool's configured default.")
    concurrency: int | None = Field(default=None, gt=0, description="-c; concurrent template executions.")
    retries: int | None = Field(default=None, ge=0, description="-retries; overrides the tool's configured default.")
    additional_arguments: list[str] = Field(default_factory=list, description="Raw flags appended after everything else.")
