"""Internal execution-engine test fixture.

Exists solely to verify :mod:`backend.execution` end-to-end -- planning,
queuing, concurrency limiting, progress reporting, cancellation, retry,
and live logging -- without running a real security tool. Per the Phase 6
brief: "This plugin does NOT execute any external program. It simply
waits, writes logs, and returns success." Unlike
:mod:`backend.plugins.sdk.process_runner` (the real, directly-tested
``asyncio.create_subprocess_exec`` path a future tool-integration phase
will use), this plugin's ``execute()`` only ``asyncio.sleep``s.

Never listed in ``backend.services.tool_service.SUPPORTED_TOOL_IDS`` and
never shown in Tool Management -- discovered by the plugin framework
exactly like any other plugin (proving discovery does not special-case
it), but purely a test fixture, like ``example-plugin``.

Behavior is controlled through ``PluginExecutionContext.extra_arguments``,
since this plugin has no real command-line flags to reflect:

- ``"duration:<seconds>"`` -- how long ``execute()`` sleeps (default 0.2s)
- ``"fail"`` -- finish with a non-zero exit code and no stdout
- ``"fail-with-output"`` -- finish with a non-zero exit code but real stdout,
  simulating a tool (e.g. Nikto hitting its own error-rate limit mid-scan)
  that still produced a partial, genuine report before exiting non-zero
- ``"raise"`` -- raise an exception instead of returning (simulates a crash)
"""

from datetime import datetime, timezone

import asyncio

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.models.health import PluginHealth
from backend.plugins.models.metadata import PluginMetadata
from backend.plugins.sdk import BasePlugin, PluginHealthStatus, get_plugin_logger

from .normalizer import normalize_dummy_output
from .parser import parse_dummy_output
from .validator import validate_dummy_target

logger = get_plugin_logger("dummy-execution")

_DEFAULT_DURATION_SECONDS = 0.2


class DummyExecutionPlugin(BasePlugin):
    """Fake, always-installed plugin that only sleeps, logs, and returns success."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata.from_manifest(self._manifest)

    def health(self) -> PluginHealth:
        return PluginHealth(
            plugin_id=self._manifest.id,
            status=PluginHealthStatus.HEALTHY,
            installed=True,
            version_detected=self._manifest.version,
            message="Dummy execution plugin has no external dependency; always healthy.",
            checked_at=datetime.now(timezone.utc),
        )

    def check_installation(self) -> bool:
        return True  # no required_binaries declared in plugin.json

    def get_version(self) -> str | None:
        return self._manifest.version

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_dummy_target(target_type, target_value)

    def prepare(self, context: PluginExecutionContext) -> None:
        context.output_directory.mkdir(parents=True, exist_ok=True)
        logger.debug("prepare() created '%s'.", context.output_directory)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        # Never passed to a real subprocess -- execute() below never starts one.
        return ["dummy-execution", "--target", context.target_value]

    async def execute(self, command: list[str], context: PluginExecutionContext) -> PluginRawOutput:
        duration = self._read_duration(context)
        should_fail = "fail" in context.extra_arguments
        should_fail_with_output = "fail-with-output" in context.extra_arguments
        should_raise = "raise" in context.extra_arguments
        logger.debug(
            "Simulating a %.2fs run against '%s' (fail=%s, fail_with_output=%s, raise=%s).",
            duration, context.target_value, should_fail, should_fail_with_output, should_raise,
        )
        await asyncio.sleep(duration)
        if should_raise:
            raise RuntimeError("simulated crash")
        if should_fail_with_output:
            return PluginRawOutput(
                stdout=f"partial dummy scan of {context.target_value}", stderr="simulated partial failure", exit_code=1
            )
        if should_fail:
            return PluginRawOutput(stdout="", stderr="simulated failure", exit_code=1)
        return PluginRawOutput(stdout=f"dummy scan of {context.target_value} complete", stderr="", exit_code=0)

    def parse(self, raw_output: PluginRawOutput) -> dict:
        return parse_dummy_output(raw_output)

    def normalize(self, parsed_output: dict) -> dict:
        return normalize_dummy_output(parsed_output)

    def cleanup(self, context: PluginExecutionContext) -> None:
        logger.debug("cleanup() called (no-op).")

    @staticmethod
    def _read_duration(context: PluginExecutionContext) -> float:
        for arg in context.extra_arguments:
            if arg.startswith("duration:"):
                try:
                    return float(arg.split(":", 1)[1])
                except ValueError:
                    break
        return _DEFAULT_DURATION_SECONDS
