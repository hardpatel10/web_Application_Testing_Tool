"""Runtime-facing plugin descriptor.

Returned by every loaded plugin's ``metadata()`` method. Always constructed
from a :class:`~backend.plugins.models.manifest.PluginManifest` via
:meth:`PluginMetadata.from_manifest` rather than populated by hand, so a
plugin's declared capabilities can never drift from its ``plugin.json``.
"""

from pydantic import BaseModel

from backend.models.enums import RawOutputFormat, TargetType
from backend.plugins.models.enums import SupportedPlatform
from backend.plugins.models.manifest import PluginManifest


class PluginMetadata(BaseModel):
    """What a plugin *is* — its identity and declared capabilities.

    Deliberately excludes ``entrypoint`` and ``dependencies``: those are
    loader concerns (how to find and instantiate the plugin), not part of
    what the tool itself is or does.
    """

    id: str
    display_name: str
    version: str
    author: str
    description: str
    homepage: str | None
    install_instructions: dict[str, str] | None
    license: str
    supported_platforms: list[SupportedPlatform]
    supported_targets: list[TargetType]
    supported_output_formats: list[RawOutputFormat]
    required_binaries: list[str]
    documentation_url: str | None

    @classmethod
    def from_manifest(cls, manifest: PluginManifest) -> "PluginMetadata":
        """Build the runtime descriptor from a plugin's manifest."""
        return cls(
            id=manifest.id,
            display_name=manifest.name,
            version=manifest.version,
            author=manifest.author,
            description=manifest.description,
            homepage=manifest.homepage,
            install_instructions=manifest.install_instructions,
            license=manifest.license,
            supported_platforms=manifest.supported_platforms,
            supported_targets=manifest.supported_targets,
            supported_output_formats=manifest.supported_output_formats,
            required_binaries=manifest.required_binaries,
            documentation_url=manifest.documentation_url,
        )
