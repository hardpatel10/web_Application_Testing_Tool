"""Service layer for Scan Profile management.

Bridges a plugin's own ``profile_manager`` (in-memory + filesystem, zero
DB/HTTP dependency — see ``backend.plugins.plugins.nmap.profile_manager``)
with the HTTP layer, translating plugin-framework exceptions into
``backend.core.exceptions`` the same way ``PluginService``/``ToolService``
already do for the rest of the plugin framework.

Every public method takes ``tool_name``, so the route surface
(``/tools/{tool_name}/profiles``) is already shaped for a second scanner
plugin to adopt the same pattern later. But only Nmap has one today.
``list_profiles``/``get_profile`` (Phase 10) return an empty list / 422
respectively for a tool with no ``profile_manager`` -- Tool Management's
generic Profiles tab needs "no profiles" to be a normal empty state, not
an error, when browsing a tool that simply doesn't have a profile system
yet. Every *mutating* endpoint (create/update/delete/duplicate/import/
enable/disable) still 422s cleanly for such a tool, since there is
nothing meaningful to mutate.

Deliberately catches :mod:`backend.plugins.exceptions`'s stable
``PluginNotFoundError``/``PluginValidationError`` — not Nmap's own
``ProfileNotFoundError``/``ProfileValidationError`` subclasses directly.
The Nmap plugin's directory is loaded as a synthetic package with its own
fresh module identity (see the Phase 4 loader's design notes in
``DECISIONS.md``), so a class imported here via the plugin's *normal*
dotted path is a different object than the one actually raised at runtime
from inside that synthetic module, even though both are named
``ProfileValidationError`` — an ``except`` naming the normally-imported
class silently never matches (caught directly via a real 500 while
testing the built-in-profile edit/delete guards). Catching the shared,
singly-loaded parent class from ``backend.plugins.exceptions`` -- which
*is* the same object everywhere -- is what actually works, since Python's
``except`` matching is ``isinstance``-based and respects that inheritance
chain regardless of which module defined the specific subclass. For the
same reason, this service never constructs a ``ScanProfile`` instance
itself for the plugin to consume — it only ever passes plain ``dict``
payloads, so ``ProfileManager`` validates them against its own,
internally-consistent ``ScanProfile`` type.
"""

from pathlib import Path

from backend.core.exceptions import InvalidInputError, NotFoundError
from backend.plugins.exceptions import PluginNotFoundError, PluginValidationError
from backend.plugins.manager.plugin_manager import PluginManager
from backend.plugins.models.execution import PluginExecutionContext
from backend.plugins.registry.registered_plugin import RegisteredPlugin
from backend.schemas.scan_profile import (
    CommandPreviewRequest,
    CommandPreviewResponse,
    ScanProfileDuplicateRequest,
    ScanProfileImportRequest,
    ScanProfileRead,
    ScanProfileWrite,
)


class ScanProfileService:
    """Business logic for browsing and managing one tool's Scan Profiles."""

    def __init__(self, plugin_manager: PluginManager) -> None:
        self._manager = plugin_manager

    def list_profiles(
        self, tool_name: str, *, query: str | None = None, category: str | None = None, risk_level: str | None = None
    ) -> list[ScanProfileRead]:
        """List/search a tool's Scan Profiles -- an empty list for a tool with no profile system.

        Deliberately does NOT 404/422 for a tool without a ``profile_manager``
        (unlike every mutating endpoint below, which still does): the Tool
        Management UI's Profiles tab needs to render a normal "no profiles"
        empty state for most of the 15 supported tools, not treat the
        absence of a profile system as a client error just because it's
        asking a generic question of a specific tool.
        """
        registered = self._get_registered_or_404(tool_name)
        profile_manager = getattr(registered.instance, "profile_manager", None)
        if profile_manager is None:
            return []
        profiles = profile_manager.search(query=query, category=category, risk_level=risk_level)
        return [self._to_read(profile, registered) for profile in profiles]

    def get_profile(self, tool_name: str, profile_id: str) -> ScanProfileRead:
        registered = self._get_registered_or_404(tool_name)
        return self._to_read(self._get_profile_or_404(tool_name, profile_id), registered)

    def create_profile(self, tool_name: str, payload: ScanProfileWrite) -> ScanProfileRead:
        registered = self._get_registered_or_404(tool_name)
        profile_manager = self._get_profile_manager(tool_name)
        try:
            return self._to_read(profile_manager.create_custom(payload.model_dump()), registered)
        except PluginValidationError as exc:
            raise InvalidInputError(str(exc)) from exc

    def update_profile(self, tool_name: str, profile_id: str, payload: ScanProfileWrite) -> ScanProfileRead:
        registered = self._get_registered_or_404(tool_name)
        profile_manager = self._get_profile_manager(tool_name)
        try:
            return self._to_read(profile_manager.update_custom(profile_id, payload.model_dump()), registered)
        except PluginNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        except PluginValidationError as exc:
            raise InvalidInputError(str(exc)) from exc

    def delete_profile(self, tool_name: str, profile_id: str) -> None:
        profile_manager = self._get_profile_manager(tool_name)
        try:
            profile_manager.delete_custom(profile_id)
        except PluginNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        except PluginValidationError as exc:
            raise InvalidInputError(str(exc)) from exc

    def duplicate_profile(self, tool_name: str, profile_id: str, payload: ScanProfileDuplicateRequest) -> ScanProfileRead:
        registered = self._get_registered_or_404(tool_name)
        profile_manager = self._get_profile_manager(tool_name)
        try:
            return self._to_read(profile_manager.duplicate(profile_id, payload.new_id, payload.new_name), registered)
        except PluginNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        except PluginValidationError as exc:
            raise InvalidInputError(str(exc)) from exc

    def import_profile(self, tool_name: str, payload: ScanProfileImportRequest) -> ScanProfileRead:
        registered = self._get_registered_or_404(tool_name)
        profile_manager = self._get_profile_manager(tool_name)
        try:
            return self._to_read(profile_manager.import_profile(payload.profile), registered)
        except PluginValidationError as exc:
            raise InvalidInputError(str(exc)) from exc

    def export_profile(self, tool_name: str, profile_id: str) -> dict:
        profile_manager = self._get_profile_manager(tool_name)
        try:
            return profile_manager.export_profile(profile_id)
        except PluginNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

    def preview_command(self, tool_name: str, payload: CommandPreviewRequest) -> CommandPreviewResponse:
        registered = self._get_registered_or_404(tool_name)
        self._get_profile_or_404(tool_name, payload.profile_id)  # 404s cleanly if unknown
        context = PluginExecutionContext(
            target_type="hostname",
            target_value=payload.target_value,
            output_directory=Path("."),
            timeout_seconds=1,
            profile_id=payload.profile_id,
            advanced_options=payload.advanced_options,
        )
        command = registered.instance.build_command(context)
        return CommandPreviewResponse(command=command)

    # -- Internal helpers -----------------------------------------------------

    def _get_registered_or_404(self, tool_name: str) -> RegisteredPlugin:
        try:
            return self._manager.get_plugin(tool_name)
        except PluginNotFoundError as exc:
            raise NotFoundError(exc.message) from exc

    def _get_profile_manager(self, tool_name: str):
        registered = self._get_registered_or_404(tool_name)
        profile_manager = getattr(registered.instance, "profile_manager", None)
        if profile_manager is None:
            raise InvalidInputError(f"'{tool_name}' does not support Scan Profiles.")
        return profile_manager

    def _get_profile_or_404(self, tool_name: str, profile_id: str):
        profile_manager = self._get_profile_manager(tool_name)
        try:
            return profile_manager.get(profile_id)
        except PluginNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

    @staticmethod
    def _to_read(profile, registered: RegisteredPlugin) -> ScanProfileRead:
        """Build the shared HTTP shape from one plugin's own ``ScanProfile`` instance.

        Uses ``getattr(..., default)`` for every field a specific plugin's
        model might not define (see ``backend.schemas.scan_profile``'s
        module docstring) -- ``profile`` here is Nmap's, Nikto's, or
        Nuclei's own distinct Pydantic model, never this shared schema.
        """
        return ScanProfileRead(
            id=profile.id,
            name=profile.name,
            description=profile.description,
            category=profile.category.value,
            icon=profile.icon,
            supported_targets=profile.supported_targets,
            arguments=profile.arguments,
            minimum_tool_version=profile.minimum_tool_version,
            risk_level=profile.risk_level.value,
            estimated_duration=profile.estimated_duration,
            built_in=profile.built_in,
            enabled=profile.id not in registered.config.disabled_profile_ids,
            required_ports=getattr(profile, "required_ports", None),
            required_scripts=getattr(profile, "required_scripts", []),
            script_args=getattr(profile, "script_args", {}),
            tuning=getattr(profile, "tuning", None),
            plugins=getattr(profile, "plugins", []),
            timeout_seconds=getattr(profile, "timeout_seconds", None),
            templates=getattr(profile, "templates", []),
            tags=getattr(profile, "tags", []),
            exclude_tags=getattr(profile, "exclude_tags", []),
            severities=getattr(profile, "severities", []),
        )
