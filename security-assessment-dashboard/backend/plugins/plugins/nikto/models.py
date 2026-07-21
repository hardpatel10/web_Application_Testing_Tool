"""Scan Profile schema: profiles are DATA, never code.

A :class:`ScanProfile` describes *what* to scan — never a literal Nikto
command string. ``command_builder.py`` is the only place a profile is ever
turned into an actual argv, so no Nikto flag for a specific profile is
ever hardcoded anywhere outside a profile's own JSON file (see
``profiles/*.json``). Mirrors ``backend.plugins.plugins.nmap.models``
field-for-field where the concept is the same (id/name/description/
category/risk_level/estimated_duration/built_in); ``tuning``/``plugins``/
``timeout_seconds`` replace Nmap's ports/scripts/timing since those are
Nikto's own tunable dimensions (``-Tuning``, ``-Plugins``, ``-timeout``).
"""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from backend.models.enums import TargetType

_ID_PATTERN_MESSAGE = "id must start with a lowercase letter and contain only lowercase letters, digits, or underscores."


class ProfileCategory(StrEnum):
    """Built-in taxonomy a Scan Profile is grouped under, for the profile browser UI."""

    QUICK = "quick"
    DEFAULT = "default"
    FULL = "full"
    SSL = "ssl"
    HEADERS = "headers"
    INTERESTING_FILES = "interesting_files"
    CGI = "cgi"
    MISCONFIGURATION = "misconfiguration"
    CUSTOM = "custom"


class RiskLevel(StrEnum):
    """How intrusive/disruptive running this profile against a target is likely to be."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScanProfile(BaseModel):
    """One reusable, named Nikto scan definition, loaded from a JSON file.

    ``tuning`` is Nikto's own ``-Tuning`` control-category codes (e.g.
    ``"1,2,3"`` — Interesting File, Misconfiguration, Information
    Disclosure); ``plugins`` is ``-Plugins`` (e.g. ``["headers"]``);
    ``arguments`` covers any other fixed flag a profile always applies
    (e.g. ``-ssl``, ``-C all``).
    """

    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    category: ProfileCategory
    icon: str = Field(default="shield-alert", max_length=50)
    supported_targets: list[TargetType] = Field(min_length=1)
    arguments: list[str] = Field(default_factory=list, description="Fixed flags this profile always applies.")
    tuning: str | None = Field(default=None, description="Nikto -Tuning codes, e.g. '1,2,3'. None uses Nikto's own default.")
    plugins: list[str] = Field(default_factory=list, description="Nikto -Plugins names, e.g. ['headers'].")
    timeout_seconds: int | None = Field(default=None, gt=0, description="Nikto's own -timeout (per-request), not the job timeout.")
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
    own value (or Nikto's own default) unchanged.
    """

    tuning: str | None = Field(default=None, description="Overrides the profile's -Tuning codes.")
    plugins: list[str] | None = Field(default=None, description="Overrides the profile's -Plugins list.")
    timeout_seconds: int | None = Field(default=None, gt=0, description="Overrides the profile's -timeout.")
    additional_arguments: list[str] = Field(default_factory=list, description="Raw flags appended after everything else.")
