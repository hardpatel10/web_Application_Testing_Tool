"""Shared base class for tool plugins that only detect and configure.

Every real tool plugin built in Phase 5 extends this class instead of
``BasePlugin`` directly. It implements the parts that are identical
across all fifteen supported tools — ``metadata()``, ``prepare()``/
``cleanup()`` (no-ops), ``execute()`` (always refuses — see below),
``check_installation()``, ``get_version()``, ``health()``, and
``diagnostics()`` — driven by three small class attributes each subclass
sets (``BINARY_NAMES``, ``VERSION_ARGS``, ``VERSION_PATTERN``). A concrete
plugin is then only ``validate_target()``, ``build_command()``,
``parse()``, and ``normalize()`` — the genuinely tool-specific parts.

``VERSION_ARGS``/``VERSION_PATTERN`` are each subclass's *best guess*, not
its only chance: ``get_version()``/``diagnostics()`` both go through
``detection_helpers.detect_version()``, which falls back through common
version-flag conventions (``-version``, ``version``, ``-v``, ``-V``) and a
generic version-number pattern if the preferred one comes up empty, so a
plugin author's regex/flag choice being slightly wrong doesn't turn into a
false "not installed".
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from backend.plugins.core.base_plugin import BasePlugin
from backend.plugins.exceptions import PluginExecutionError
from backend.plugins.models.diagnostics import PluginDiagnostics
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.models.health import PluginHealth
from backend.plugins.models.enums import PluginHealthStatus
from backend.plugins.models.metadata import PluginMetadata
from backend.plugins.sdk.detection_helpers import detect_version, resolve_executable_detailed


class DetectionOnlyPlugin(BasePlugin):
    """A plugin that detects, validates, and configures a tool but never runs it.

    ``execute()`` always raises :class:`PluginExecutionError`: there is no
    task queue or orchestrator yet, and this phase's brief is explicit that
    tool execution is out of scope. ``build_command()`` remains real,
    per-tool string construction (pure, no subprocess) so the Tool Details
    panel can show what *would* run, and so a future execution phase can be
    built against this same contract without changing it.
    """

    BINARY_NAMES: ClassVar[list[str]] = []
    VERSION_ARGS: ClassVar[list[str]] = ["--version"]
    VERSION_PATTERN: ClassVar[str] = r"(\d+\.\d+(?:\.\d+)?)"

    def metadata(self) -> PluginMetadata:
        return PluginMetadata.from_manifest(self._manifest)

    def resolve_executable(self) -> Path | None:
        executable, _method = resolve_executable_detailed(
            self.BINARY_NAMES, custom_path=self._config.custom_executable_path
        )
        return executable

    def check_installation(self) -> bool:
        return self.resolve_executable() is not None

    def get_version(self) -> str | None:
        executable = self.resolve_executable()
        if executable is None:
            return None
        return detect_version(executable, preferred_args=self.VERSION_ARGS, pattern=self.VERSION_PATTERN).version

    def diagnostics(self) -> PluginDiagnostics:
        """Everything the Diagnostics tab needs — one implementation shared by every tool plugin.

        Detects the executable and version exactly once (unlike calling
        :meth:`resolve_executable`/:meth:`get_version`/:meth:`health`
        separately, which would re-run the same subprocess detection up to
        three times), then builds the same health verdict :meth:`health`
        would via the shared :meth:`_build_health` helper.
        """
        executable, method = resolve_executable_detailed(
            self.BINARY_NAMES, custom_path=self._config.custom_executable_path
        )
        version_result = (
            detect_version(executable, preferred_args=self.VERSION_ARGS, pattern=self.VERSION_PATTERN)
            if executable is not None
            else None
        )
        version = version_result.version if version_result else None
        health = self._build_health(executable, version)
        return PluginDiagnostics(
            plugin_id=self._manifest.id,
            binary_names=list(self.BINARY_NAMES),
            custom_executable_path=str(self._config.custom_executable_path)
            if self._config.custom_executable_path
            else None,
            resolved_path=str(executable) if executable else None,
            detection_method=method,
            version_command=version_result.command if version_result else None,
            raw_version_output=(version_result.raw_output or None) if version_result else None,
            detected_version=version,
            health_status=health.status,
            health_message=health.message,
            checked_at=health.checked_at,
        )

    def health(self) -> PluginHealth:
        executable = self.resolve_executable()
        version = self.get_version() if executable else None
        return self._build_health(executable, version)

    def _build_health(self, executable: Path | None, version: str | None) -> PluginHealth:
        """Shared health verdict used by both :meth:`health` and :meth:`diagnostics`."""
        if executable is None:
            status = PluginHealthStatus.NOT_INSTALLED
            message = (
                f"'{self._manifest.id}' was not found on PATH, in common installation directories, "
                "or at the configured custom executable path."
            )
        elif version is None:
            status = PluginHealthStatus.DEGRADED
            message = f"Found '{executable}' but could not determine its version."
        else:
            status = PluginHealthStatus.HEALTHY
            message = f"'{self._manifest.id}' v{version} at '{executable}'."

        return PluginHealth(
            plugin_id=self._manifest.id,
            status=status,
            installed=executable is not None,
            version_detected=version,
            message=message,
            checked_at=datetime.now(timezone.utc),
        )

    def prepare(self, context: PluginExecutionContext) -> None:
        return None

    async def execute(self, command: list[str], context: PluginExecutionContext) -> PluginRawOutput:
        raise PluginExecutionError(
            f"'{self._manifest.id}' detects and configures this tool but does not execute it — "
            "tool execution is a future phase's task-queue/orchestrator, out of scope here.",
            plugin_id=self._manifest.id,
        )

    def cleanup(self, context: PluginExecutionContext) -> None:
        return None
