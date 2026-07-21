"""Internal reference plugin.

Exists solely to verify the plugin framework end-to-end: discovery,
manifest/structure/interface validation, dynamic loading, and
registration. It implements every ``BasePlugin`` method with fixed,
canned behavior and:

- never executes a subprocess or any external binary
- never contacts a real target
- never produces a real finding

This plugin is not imported or referenced anywhere in the application
core — the framework discovers and loads it purely by scanning
``backend/plugins/plugins/`` at runtime, exactly as it would any future
real tool plugin.
"""

from datetime import datetime, timezone

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.models.health import PluginHealth
from backend.plugins.models.metadata import PluginMetadata
from backend.plugins.sdk import BasePlugin, PluginHealthStatus, get_plugin_logger

from .normalizer import normalize_example_output
from .parser import parse_example_output
from .validator import validate_example_target

logger = get_plugin_logger("example-plugin")


class ExamplePlugin(BasePlugin):
    """Reference implementation exercising every required interface method."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata.from_manifest(self._manifest)

    def health(self) -> PluginHealth:
        return PluginHealth(
            plugin_id=self._manifest.id,
            status=PluginHealthStatus.HEALTHY,
            installed=self.check_installation(),
            version_detected=self.get_version(),
            message="Example plugin has no external dependency, so it is always healthy.",
            checked_at=datetime.now(timezone.utc),
        )

    def check_installation(self) -> bool:
        return True  # no required_binaries declared in plugin.json

    def get_version(self) -> str | None:
        return self._manifest.version

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_example_target(target_type, target_value)

    def prepare(self, context: PluginExecutionContext) -> None:
        logger.debug("prepare() called for target '%s' (no-op).", context.target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        # Never passed to execute() by anything in this phase - no task
        # queue or orchestrator exists yet to invoke it.
        return ["example-tool", "--target", context.target_value]

    async def execute(self, command: list[str], context: PluginExecutionContext) -> PluginRawOutput:
        logger.debug("execute() called with a fixed result; no subprocess is ever started.")
        return PluginRawOutput(stdout='{"example": true}', stderr="", exit_code=0)

    def parse(self, raw_output: PluginRawOutput) -> dict:
        return parse_example_output(raw_output)

    def normalize(self, parsed_output: dict) -> dict:
        return normalize_example_output(parsed_output)

    def cleanup(self, context: PluginExecutionContext) -> None:
        logger.debug("cleanup() called (no-op).")
