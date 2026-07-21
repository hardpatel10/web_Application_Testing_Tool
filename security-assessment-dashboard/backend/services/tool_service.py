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
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import InvalidInputError, NotFoundError
from backend.models.enums import ToolHealthStatus, ToolStatus
from backend.models.tool import Tool, ToolConfiguration
from backend.plugins.exceptions import PluginNotFoundError
from backend.plugins.manager.plugin_manager import PluginManager
from backend.plugins.models.enums import PluginHealthStatus
from backend.plugins.registry.registered_plugin import RegisteredPlugin
from backend.plugins.sdk.detection_helpers import validate_custom_executable
from backend.schemas.tool import (
    FilesystemBrowseResponse,
    FilesystemEntry,
    ToolConfigurationRead,
    ToolConfigurationUpdate,
    ToolDetail,
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

            if await self._get_configuration_row(tool.id) is None:
                self._session.add(ToolConfiguration(tool_id=tool.id))
                await self._session.flush()
        return not_loaded

    async def _refresh_tool_state(self, registered: RegisteredPlugin) -> None:
        """Run a live check_installation/get_version/health pass and persist the result."""
        tool = await self._get_tool_row(registered.manifest.id)
        if tool is None:
            return

        instance = registered.instance
        health = instance.health()
        executable = instance.resolve_executable()

        tool.is_installed = health.installed
        tool.version = health.version_detected
        tool.installation_path = str(executable) if executable else None
        tool.health_status = _HEALTH_STATUS_MAP.get(health.status, ToolHealthStatus.WARNING)
        tool.health_message = health.message
        tool.last_checked_at = health.checked_at
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

    async def validate_tools(self, name: str | None) -> list[ToolValidationResult]:
        names = [name] if name else list(SUPPORTED_TOOL_IDS)
        results = []
        for tool_name in names:
            try:
                registered = self._get_registered_or_404(tool_name)
            except NotFoundError as exc:
                results.append(ToolValidationResult(name=tool_name, valid=False, errors=[exc.message], warnings=[]))
                continue
            results.append(await self._validate_one(tool_name, registered))
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

        if registered.instance.check_installation() and registered.instance.get_version() is None:
            warnings.append(f"'{name}' is installed but its version could not be determined.")

        missing_dependencies = self._manager.check_dependencies(name)
        if missing_dependencies:
            errors.append(f"Missing dependencies: {', '.join(missing_dependencies)}.")

        return ToolValidationResult(name=name, valid=not errors, errors=errors, warnings=warnings)

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
        validation_results = await self.validate_tools(tool.name)
        validation = validation_results[0]

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
            installation_path=tool.installation_path,
            status=tool.status,
            health_status=tool.health_status,
            health_message=tool.health_message,
            enabled=tool.enabled,
            is_installed=tool.is_installed,
            last_checked_at=tool.last_checked_at,
            supported_platforms=[platform.value for platform in metadata.supported_platforms],
            supported_targets=metadata.supported_targets,
            supported_output_formats=metadata.supported_output_formats,
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
