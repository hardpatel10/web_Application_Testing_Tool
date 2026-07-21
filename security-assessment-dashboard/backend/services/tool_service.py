"""Service layer for Tool Management.

Bridges the plugin framework (``backend.plugins`` — in-memory, source of
truth for what a tool *declares*) with persistent storage (``Tool``/
``ToolConfiguration`` DB rows — source of truth for discovery *results*
and user *configuration*). This is the only place that translates
between ``backend.plugins.models.config.PluginConfiguration`` (the live,
in-memory object a running plugin reads) and
``backend.models.tool.ToolConfiguration`` (the persisted row).

Scoped to :data:`SUPPORTED_TOOL_IDS` — the 15 tools this phase supports.
Phase 4's generic ``/plugins`` API is untouched and still reports every
registered plugin, including the internal, non-tool ``example-plugin``.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import InvalidInputError, NotFoundError
from backend.models.enums import ToolHealthStatus, ToolOverallStatus, ToolStatus
from backend.models.tool import Tool, ToolConfiguration
from backend.plugins.exceptions import PluginNotFoundError
from backend.plugins.manager.plugin_manager import PluginManager
from backend.plugins.models.enums import PluginHealthStatus
from backend.plugins.registry.registered_plugin import RegisteredPlugin
from backend.plugins.sdk.detection_helpers import is_version_at_least, validate_custom_executable
from backend.schemas.tool import (
    FilesystemBrowseResponse,
    FilesystemEntry,
    ToolConfigurationRead,
    ToolConfigurationUpdate,
    ToolDetail,
    ToolDiagnostics,
    ToolDiscoveryResponse,
    ToolHealthResponse,
    ToolSummary,
    ToolValidationResult,
)

logger = logging.getLogger(__name__)

SUPPORTED_TOOL_IDS: tuple[str, ...] = (
    "nmap",
    "nuclei",
    "whatweb",
    "nikto",
    "httpx",
    "gobuster",
    "dirsearch",
    "feroxbuster",
    "ffuf",
    "sslscan",
    "katana",
    "naabu",
    "subfinder",
    "amass",
    "dnsx",
)

_HEALTH_STATUS_MAP: dict[PluginHealthStatus, ToolHealthStatus] = {
    PluginHealthStatus.HEALTHY: ToolHealthStatus.HEALTHY,
    PluginHealthStatus.DEGRADED: ToolHealthStatus.WARNING,
    PluginHealthStatus.UNKNOWN: ToolHealthStatus.WARNING,
    PluginHealthStatus.NOT_INSTALLED: ToolHealthStatus.ERROR,
    PluginHealthStatus.UNHEALTHY: ToolHealthStatus.ERROR,
}

_SORT_FIELDS = {"name", "display_name", "status", "version", "last_checked_at"}

#: Environment variable names always worth surfacing in Diagnostics if set, regardless of
#: per-tool configuration -- these are what actually influence PATH-based detection/execution.
_ALWAYS_RELEVANT_ENV_VARS = ("PATH", "HOME")


def derive_overall_status(status: ToolStatus, health_status: ToolHealthStatus | None) -> ToolOverallStatus:
    """Collapse the two independent status dimensions into the single badge Tool Management shows.

    Precedence: the user's own choice (disabled) and hard lifecycle facts
    (missing, unsupported version) always win over health, since health is
    meaningless for a tool that isn't even installed or is turned off.
    ``MISCONFIGURED`` has no dedicated slot in the unified vocabulary — a
    misconfiguration is an error condition, so it maps to ``ERROR``.
    """
    if status == ToolStatus.DISABLED:
        return ToolOverallStatus.DISABLED
    if status == ToolStatus.MISSING:
        return ToolOverallStatus.MISSING
    if status == ToolStatus.UNSUPPORTED_VERSION:
        return ToolOverallStatus.UNSUPPORTED_VERSION
    if status == ToolStatus.MISCONFIGURED:
        return ToolOverallStatus.ERROR
    if health_status == ToolHealthStatus.HEALTHY:
        return ToolOverallStatus.HEALTHY
    if health_status == ToolHealthStatus.ERROR:
        return ToolOverallStatus.ERROR
    return ToolOverallStatus.WARNING


class ToolService:
    """Business logic for discovering, configuring, and monitoring supported tools."""

    def __init__(self, session: AsyncSession, plugin_manager: PluginManager) -> None:
        self._session = session
        self._manager = plugin_manager

    # -- Discovery / sync --------------------------------------------------

    async def discover(self) -> ToolDiscoveryResponse:
        """Re-scan plugin directories, then re-detect and persist every supported tool's state."""
        self._manager.discover_and_register()
        not_loaded = await self._sync_catalog()

        for tool_id in SUPPORTED_TOOL_IDS:
            try:
                registered = self._manager.get_plugin(tool_id)
            except PluginNotFoundError:
                continue
            await self._refresh_tool_state(registered)

        await self._session.flush()
        return ToolDiscoveryResponse(tools=await self.list_tools(), not_loaded=not_loaded)

    async def _sync_catalog(self) -> list[str]:
        """Ensure a Tool + ToolConfiguration row exists for every supported, registered plugin.

        Returns supported tool ids with no matching registered plugin (e.g.
        its directory failed validation) — reported honestly, never
        fabricated as a "missing" Tool row.
        """
        not_loaded: list[str] = []
        for tool_id in SUPPORTED_TOOL_IDS:
            try:
                registered = self._manager.get_plugin(tool_id)
            except PluginNotFoundError:
                not_loaded.append(tool_id)
                continue

            tool = await self._get_tool_row(tool_id)
            metadata = registered.instance.metadata()
            if tool is None:
                tool = Tool(name=tool_id, display_name=metadata.display_name, status=ToolStatus.MISSING)
                self._session.add(tool)
                await self._session.flush()
            else:
                tool.display_name = metadata.display_name

            row = await self._get_configuration_row(tool.id)
            if row is None:
                row = ToolConfiguration(tool_id=tool.id)
                self._session.add(row)
                await self._session.flush()

            # Real bug fixed here: previously nothing re-applied a persisted ToolConfiguration
            # row onto the live (in-memory) PluginConfiguration after a process restart -- only
            # an explicit PUT /tools/{name}/configuration call did, via _apply_to_live_config.
            # That meant a saved custom executable path/proxy/timeout/etc. silently stopped
            # taking effect the moment the backend process restarted, even though the DB still
            # showed it as configured, until the user re-submitted the same settings again.
            # Applying it here too (every discover()/sync pass, which also runs at the top of
            # every _refresh_tool_state loop) makes persisted configuration actually persist.
            self._apply_to_live_config(registered, row)
        return not_loaded

    async def _refresh_tool_state(self, registered: RegisteredPlugin) -> None:
        """Run a live detection/version/health pass and persist the result."""
        tool = await self._get_tool_row(registered.manifest.id)
        if tool is None:
            return

        diagnostics = registered.instance.diagnostics()

        tool.is_installed = diagnostics.resolved_path is not None
        tool.version = diagnostics.detected_version
        tool.installation_path = diagnostics.resolved_path
        tool.health_status = _HEALTH_STATUS_MAP.get(diagnostics.health_status, ToolHealthStatus.WARNING)
        tool.health_message = diagnostics.health_message
        tool.last_checked_at = diagnostics.checked_at
        tool.status = self._derive_status(tool, registered)
        await self._session.flush()

    def _derive_status(self, tool: Tool, registered: RegisteredPlugin) -> ToolStatus:
        """Map discovery/config facts to the coarse lifecycle status the UI shows.

        Not enabled always wins (user's own choice). Otherwise: not found on
        disk -> MISSING; found but a configured custom path/wordlist fails
        validation -> MISCONFIGURED; found but no version string could be
        parsed at all -> UNSUPPORTED_VERSION (this platform has no way to
        act on a tool whose version output it can't even read); otherwise
        INSTALLED.
        """
        if not tool.enabled:
            return ToolStatus.DISABLED
        if not tool.is_installed:
            return ToolStatus.MISSING

        config = registered.config
        if config.custom_executable_path is not None:
            errors = validate_custom_executable(config.custom_executable_path, registered.instance.BINARY_NAMES)
            if errors:
                return ToolStatus.MISCONFIGURED
        for wordlist_path in config.wordlists.values():
            if not Path(wordlist_path).is_file():
                return ToolStatus.MISCONFIGURED

        if tool.version is None:
            return ToolStatus.UNSUPPORTED_VERSION
        return ToolStatus.INSTALLED

    # -- Queries -------------------------------------------------------------

    async def list_tools(
        self, *, search: str | None = None, status_filter: ToolStatus | None = None,
        health_filter: ToolHealthStatus | None = None, sort_by: str = "name", sort_desc: bool = False,
    ) -> list[ToolSummary]:
        if sort_by not in _SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort tools by '{sort_by}'.")

        conditions = [Tool.name.in_(SUPPORTED_TOOL_IDS)]
        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append((Tool.name.ilike(term)) | (Tool.display_name.ilike(term)))
        if status_filter is not None:
            conditions.append(Tool.status == status_filter)
        if health_filter is not None:
            conditions.append(Tool.health_status == health_filter)

        sort_column = getattr(Tool, sort_by)
        order_by = sort_column.desc() if sort_desc else sort_column.asc()
        stmt = select(Tool).where(*conditions).order_by(order_by)
        tools = list((await self._session.execute(stmt)).scalars().all())
        return [self._to_summary(tool) for tool in tools]

    async def get_tool(self, name: str) -> ToolDetail:
        tool = await self._get_tool_or_404(name)
        registered = self._get_registered_or_404(name)
        return await self._to_detail(tool, registered)

    async def get_health(self, name: str) -> ToolHealthResponse:
        """Run a fresh, live health check (not the last-cached DB values) and persist it."""
        registered = self._get_registered_or_404(name)
        await self._refresh_tool_state(registered)
        health = registered.instance.health()
        return ToolHealthResponse(
            name=name,
            status=_HEALTH_STATUS_MAP.get(health.status, ToolHealthStatus.WARNING),
            installed=health.installed,
            version_detected=health.version_detected,
            message=health.message,
            checked_at=health.checked_at,
        )

    async def refresh_tool(self, name: str) -> ToolDetail:
        """Re-run detection/version/health for exactly this one tool and return its updated detail.

        Distinct from ``discover()`` (re-scans plugin *directories* for every
        supported tool from scratch, POST /tools/discover) — this is the
        lighter, per-tool ``POST /tools/{name}/refresh`` a user hits from
        the Tool Details page after e.g. installing the binary or updating
        PATH, without needing a full re-discovery pass.
        """
        tool = await self._get_tool_or_404(name)
        registered = self._get_registered_or_404(name)
        await self._refresh_tool_state(registered)
        return await self._to_detail(tool, registered)

    async def get_diagnostics(self, name: str) -> ToolDiagnostics:
        """Everything the Diagnostics tab shows: not just whether a tool is healthy, but why."""
        registered = self._get_registered_or_404(name)
        diagnostics = registered.instance.diagnostics()
        validation = await self._validate_one(name, registered)

        path_directories = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
        environment_variables: dict[str, str] = {}
        for var_name in _ALWAYS_RELEVANT_ENV_VARS:
            value = os.environ.get(var_name)
            if value:
                environment_variables[var_name] = value
        environment_variables.update(registered.config.environment_variables)
        for proxy_var, value in (
            ("HTTP_PROXY", registered.config.http_proxy),
            ("HTTPS_PROXY", registered.config.https_proxy),
            ("SOCKS_PROXY", registered.config.socks_proxy),
        ):
            if value:
                environment_variables[proxy_var] = value

        return ToolDiagnostics(
            name=name,
            binary_names=diagnostics.binary_names,
            custom_executable_path=diagnostics.custom_executable_path,
            resolved_path=diagnostics.resolved_path,
            detection_method=diagnostics.detection_method,
            version_command=diagnostics.version_command,
            raw_version_output=diagnostics.raw_version_output,
            detected_version=diagnostics.detected_version,
            health_status=_HEALTH_STATUS_MAP.get(diagnostics.health_status),
            health_message=diagnostics.health_message,
            path_directories=path_directories,
            environment_variables=environment_variables,
            validation_errors=validation.errors,
            validation_warnings=validation.warnings,
            checked_at=diagnostics.checked_at,
        )

    async def validate_tools(self, name: str | None) -> list[ToolValidationResult]:
        names = [name] if name else list(SUPPORTED_TOOL_IDS)
        results = []
        for tool_name in names:
            try:
                registered = self._get_registered_or_404(tool_name)
            except NotFoundError as exc:
                results.append(ToolValidationResult(name=tool_name, valid=False, errors=[exc.message], warnings=[]))
                continue
            result = await self._validate_one(tool_name, registered)
            results.append(result)

            tool = await self._get_tool_row(tool_name)
            if tool is not None:
                tool.last_validated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return results

    async def _validate_one(self, name: str, registered: RegisteredPlugin) -> ToolValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        config = registered.config

        if config.custom_executable_path is not None:
            errors.extend(validate_custom_executable(config.custom_executable_path, registered.instance.BINARY_NAMES))
        elif not registered.instance.check_installation():
            warnings.append(f"'{name}' was not found on this machine.")

        for slot, path in config.wordlists.items():
            if not Path(path).is_file():
                errors.append(f"Wordlist '{slot}' does not point to an existing file: '{path}'.")

        detected_version = registered.instance.get_version() if registered.instance.check_installation() else None
        if registered.instance.check_installation() and detected_version is None:
            warnings.append(f"'{name}' is installed but its version could not be determined.")

        minimum_version = registered.instance.metadata().minimum_tool_version
        if detected_version is not None and minimum_version is not None:
            if not is_version_at_least(detected_version, minimum_version):
                warnings.append(
                    f"Detected version {detected_version} is older than the minimum supported "
                    f"version {minimum_version}; results may be unreliable."
                )

        missing_dependencies = self._manager.check_dependencies(name)
        if missing_dependencies:
            errors.append(f"Missing dependencies: {', '.join(missing_dependencies)}.")

        return ToolValidationResult(name=name, valid=not errors, errors=errors, warnings=warnings)

    # -- Scan Profile enable/disable ------------------------------------------

    async def set_profile_enabled(self, name: str, profile_id: str, *, enabled: bool) -> None:
        """Toggle whether ``profile_id`` is offered for new scans of tool ``name``.

        Persisted on ``ToolConfiguration.disabled_profiles_json`` and pushed
        immediately onto the live ``PluginConfiguration`` (no reload
        needed), the same pattern every other configuration change in this
        service follows. Works uniformly for built-in and custom profiles —
        disabling never edits or deletes the profile itself.
        """
        tool = await self._get_tool_or_404(name)
        registered = self._get_registered_or_404(name)
        row = await self._get_configuration_row(tool.id)
        if row is None:
            row = ToolConfiguration(tool_id=tool.id)
            self._session.add(row)

        disabled = set(row.disabled_profiles_json or [])
        if enabled:
            disabled.discard(profile_id)
        else:
            disabled.add(profile_id)
        row.disabled_profiles_json = sorted(disabled)
        await self._session.flush()
        registered.config.disabled_profile_ids = list(row.disabled_profiles_json)

    # -- Configuration --------------------------------------------------------

    async def update_configuration(self, name: str, payload: ToolConfigurationUpdate) -> ToolDetail:
        tool = await self._get_tool_or_404(name)
        registered = self._get_registered_or_404(name)
        row = await self._get_configuration_row(tool.id)
        if row is None:
            row = ToolConfiguration(tool_id=tool.id)
            self._session.add(row)

        updates = payload.model_dump(exclude_unset=True)

        if "enabled" in updates:
            tool.enabled = updates.pop("enabled")
            registered.config.enabled = tool.enabled

        if "custom_executable_path" in updates and updates["custom_executable_path"]:
            candidate = Path(updates["custom_executable_path"])
            errors = validate_custom_executable(candidate, registered.instance.BINARY_NAMES)
            if errors:
                raise InvalidInputError("; ".join(errors))

        for key in ("wordlists",):
            if updates.get(key):
                for slot, path in updates[key].items():
                    if not Path(path).is_file():
                        raise InvalidInputError(f"Wordlist '{slot}' does not point to an existing file: '{path}'.")

        for field, value in updates.items():
            if field == "arguments":
                row.arguments_json = value
            elif field == "environment_variables":
                row.environment_json = value
            elif field == "wordlists":
                row.wordlists_json = value
            else:
                setattr(row, field, value)

        await self._session.flush()
        self._apply_to_live_config(registered, row)
        await self._refresh_tool_state(registered)
        return await self._to_detail(tool, registered)

    @staticmethod
    def _apply_to_live_config(registered: RegisteredPlugin, row: ToolConfiguration) -> None:
        """Push the persisted row onto the shared, live PluginConfiguration object.

        Mutates ``registered.config`` in place (it is the *same object* the
        running plugin instance reads via ``self._config`` — see
        ``PluginLoader``) so a saved configuration change takes effect
        immediately, with no reload required.
        """
        config = registered.config
        config.default_timeout_seconds = row.timeout or config.default_timeout_seconds
        config.working_directory = Path(row.working_directory) if row.working_directory else None
        config.custom_executable_path = Path(row.custom_executable_path) if row.custom_executable_path else None
        config.http_proxy = row.http_proxy
        config.https_proxy = row.https_proxy
        config.socks_proxy = row.socks_proxy
        config.rate_limit = row.rate_limit
        config.retries = row.retries
        config.output_directory = Path(row.output_directory) if row.output_directory else None
        config.temp_directory = Path(row.temp_directory) if row.temp_directory else None
        config.arguments = list(row.arguments_json or [])
        config.environment_variables = dict(row.environment_json or {})
        config.wordlists = {slot: Path(path) for slot, path in (row.wordlists_json or {}).items()}
        config.disabled_profile_ids = list(row.disabled_profiles_json or [])

    # -- Filesystem browse (wordlist / path picker) --------------------------

    @staticmethod
    def browse_filesystem(path: str | None) -> FilesystemBrowseResponse:
        target = Path(path) if path else Path.home()
        if not target.is_dir():
            raise InvalidInputError(f"'{target}' is not a directory.")

        entries = []
        try:
            for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                try:
                    entries.append(FilesystemEntry(name=entry.name, path=str(entry), is_directory=entry.is_dir()))
                except OSError:
                    continue
        except PermissionError as exc:
            raise InvalidInputError(f"Permission denied reading '{target}'.") from exc

        return FilesystemBrowseResponse(path=str(target), parent=str(target.parent) if target.parent != target else None, entries=entries)

    # -- Internal helpers -----------------------------------------------------

    async def _get_tool_row(self, name: str) -> Tool | None:
        stmt = select(Tool).where(Tool.name == name)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def _get_tool_or_404(self, name: str) -> Tool:
        tool = await self._get_tool_row(name)
        if tool is None:
            raise NotFoundError(f"Tool '{name}' not found. Run discovery (POST /tools/discover) first.")
        return tool

    async def _get_configuration_row(self, tool_id) -> ToolConfiguration | None:
        stmt = select(ToolConfiguration).where(ToolConfiguration.tool_id == tool_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    def _get_registered_or_404(self, name: str) -> RegisteredPlugin:
        try:
            return self._manager.get_plugin(name)
        except PluginNotFoundError as exc:
            raise NotFoundError(exc.message) from exc

    def _to_summary(self, tool: Tool) -> ToolSummary:
        try:
            registered = self._manager.get_plugin(tool.name)
            metadata = registered.instance.metadata()
            supported_targets = metadata.supported_targets
            supported_output_formats = metadata.supported_output_formats
        except PluginNotFoundError:
            supported_targets = []
            supported_output_formats = []

        return ToolSummary(
            id=str(tool.id),
            name=tool.name,
            display_name=tool.display_name,
            version=tool.version,
            status=tool.status,
            health_status=tool.health_status,
            overall_status=derive_overall_status(tool.status, tool.health_status),
            enabled=tool.enabled,
            is_installed=tool.is_installed,
            last_checked_at=tool.last_checked_at,
            supported_targets=supported_targets,
            supported_output_formats=supported_output_formats,
        )

    async def _to_detail(self, tool: Tool, registered: RegisteredPlugin) -> ToolDetail:
        metadata = registered.instance.metadata()
        row = await self._get_configuration_row(tool.id)
        row = row or ToolConfiguration(tool_id=tool.id)
        # Read-only validation for display -- deliberately NOT validate_tools(), which also
        # stamps last_validated_at; that timestamp should only move on an explicit validate
        # action (POST /tools/{name}/validate), not every time this detail view is fetched.
        validation = await self._validate_one(tool.name, registered)
        diagnostics = registered.instance.diagnostics()

        return ToolDetail(
            id=str(tool.id),
            name=tool.name,
            display_name=tool.display_name,
            description=metadata.description,
            homepage=metadata.homepage,
            documentation_url=metadata.documentation_url,
            install_instructions=metadata.install_instructions,
            license=metadata.license,
            version=tool.version,
            minimum_tool_version=metadata.minimum_tool_version,
            recommended_tool_version=metadata.recommended_tool_version,
            installation_path=tool.installation_path,
            detection_method=diagnostics.detection_method,
            status=tool.status,
            health_status=tool.health_status,
            health_message=tool.health_message,
            overall_status=derive_overall_status(tool.status, tool.health_status),
            enabled=tool.enabled,
            is_installed=tool.is_installed,
            last_checked_at=tool.last_checked_at,
            last_validated_at=tool.last_validated_at,
            supported_platforms=[platform.value for platform in metadata.supported_platforms],
            supported_targets=metadata.supported_targets,
            supported_output_formats=metadata.supported_output_formats,
            supports_profiles=getattr(registered.instance, "profile_manager", None) is not None,
            required_binaries=metadata.required_binaries,
            dependencies=registered.manifest.dependencies,
            missing_dependencies=self._manager.check_dependencies(tool.name),
            configuration=ToolConfigurationRead(
                timeout=row.timeout,
                working_directory=row.working_directory,
                custom_executable_path=row.custom_executable_path,
                http_proxy=row.http_proxy,
                https_proxy=row.https_proxy,
                socks_proxy=row.socks_proxy,
                rate_limit=row.rate_limit,
                retries=row.retries,
                output_directory=row.output_directory,
                temp_directory=row.temp_directory,
                arguments=row.arguments_json or [],
                environment_variables=row.environment_json or {},
                wordlists=row.wordlists_json or {},
            ),
            validation_valid=validation.valid,
            validation_errors=validation.errors,
            validation_warnings=validation.warnings,
            created_at=tool.created_at,
        )
