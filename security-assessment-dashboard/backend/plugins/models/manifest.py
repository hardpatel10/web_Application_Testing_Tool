"""``plugin.json`` manifest schema.

The manifest is the single declarative source of truth for a plugin's
identity and capabilities. :class:`backend.plugins.models.metadata.PluginMetadata`
(the object a loaded plugin's ``metadata()`` method returns at runtime) is
always derived from a manifest via :meth:`PluginMetadata.from_manifest`, so
there is exactly one place these fields are typed and validated.
"""

import re

from pydantic import BaseModel, Field, field_validator

from backend.models.enums import RawOutputFormat, TargetType
from backend.plugins.models.enums import SupportedPlatform

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
_ENTRYPOINT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*$")


class PluginManifest(BaseModel):
    """Typed representation of a plugin's ``plugin.json`` file.

    Field-level validation (this model) covers syntactic correctness only —
    directory-structure and interface-compliance checks live in
    ``backend.plugins.validators`` and require filesystem/import access this
    model deliberately does not have.
    """

    id: str = Field(description="Stable, unique plugin identifier (lowercase, hyphens/underscores).")
    name: str = Field(min_length=1, max_length=200, description="Human-readable display name.")
    version: str = Field(description="Semantic version, e.g. '1.0.0'.")
    entrypoint: str = Field(description="'<module_stem>:<ClassName>' resolved relative to the plugin directory.")
    author: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    license: str = Field(min_length=1, max_length=100)
    homepage: str | None = None
    documentation_url: str | None = None
    install_instructions: dict[str, str] | None = Field(
        default=None,
        description="Per-platform ('windows'/'linux'/'macos') plain-text install guidance, "
        "shown in Tool Management when the tool isn't installed. Never a download/execution "
        "action the application takes itself -- detect, validate, and guide only.",
    )
    supported_platforms: list[SupportedPlatform] = Field(min_length=1)
    supported_targets: list[TargetType] = Field(min_length=1)
    supported_output_formats: list[RawOutputFormat] = Field(min_length=1)
    required_binaries: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(
        default_factory=list,
        description="Plugin IDs this plugin depends on being registered alongside it.",
    )
    minimum_tool_version: str | None = Field(
        default=None,
        description="Oldest tool version this plugin is known to work correctly against, if any. "
        "Used by validation to warn (never block) when a detected version is older.",
    )
    recommended_tool_version: str | None = Field(
        default=None,
        description="Tool version this plugin is developed/tested against, if any. Informational only.",
    )

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if not _ID_PATTERN.match(value):
            raise ValueError("id must start with a lowercase letter and contain only lowercase letters, digits, '-', or '_'.")
        return value

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        if not _VERSION_PATTERN.match(value):
            raise ValueError("version must be a semantic version, e.g. '1.0.0' or '1.0.0-beta.1'.")
        return value

    @field_validator("entrypoint")
    @classmethod
    def _validate_entrypoint(cls, value: str) -> str:
        if not _ENTRYPOINT_PATTERN.match(value):
            raise ValueError("entrypoint must be in the form '<module_stem>:<ClassName>', e.g. 'plugin:ExamplePlugin'.")
        return value

    @field_validator("dependencies")
    @classmethod
    def _validate_dependency_ids(cls, value: list[str]) -> list[str]:
        for dependency_id in value:
            if not _ID_PATTERN.match(dependency_id):
                raise ValueError(f"'{dependency_id}' is not a valid plugin id.")
        return value
