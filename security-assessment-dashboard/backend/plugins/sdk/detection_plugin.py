"""Shared base class for tool plugins that only detect and configure.

Every real tool plugin built in Phase 5 extends this class instead of
``BasePlugin`` directly. It implements the parts that are identical
across all fifteen supported tools — ``metadata()``, ``prepare()``/
``cleanup()`` (no-ops), ``execute()`` (always refuses — see below),
``check_installation()``, ``get_version()``, and ``health()`` — driven by
three small class attributes each subclass sets (``BINARY_NAMES``,
``VERSION_ARGS``, ``VERSION_PATTERN``). A concrete plugin is then only
``validate_target()``, ``build_command()``, ``parse()``, and
``normalize()`` — the genuinely tool-specific parts.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from backend.plugins.core.base_plugin import BasePlugin
from backend.plugins.exceptions import PluginExecutionError
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.models.health import PluginHealth
from backend.plugins.models.enums import PluginHealthStatus
from backend.plugins.models.metadata import PluginMetadata
from backend.plugins.sdk.detection_helpers import extract_version, find_executable, run_version_command


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
        return find_executable(self.BINARY_NAMES, custom_path=self._config.custom_executable_path)

    def check_installation(self) -> bool:
        return self.resolve_executable() is not None

    def get_version(self) -> str | None:
        executable = self.resolve_executable()
        if executable is None:
            return None
        stdout, stderr, _return_code = run_version_command(executable, self.VERSION_ARGS)
        return extract_version(f"{stdout}\n{stderr}", self.VERSION_PATTERN)

    def health(self) -> PluginHealth:
        executable = self.resolve_executable()
        version = self.get_version() if executable else None

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
