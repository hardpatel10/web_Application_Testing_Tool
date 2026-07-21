"""Katana plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_katana_output
from .parser import parse_katana_output
from .validator import validate_katana_target

logger = get_plugin_logger("katana")


class KatanaPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["katana"]
    VERSION_ARGS = ["-version"]
    VERSION_PATTERN = r"v?(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_katana_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "katana", "-u", context.target_value, *self._config.arguments]
        if self._config.rate_limit:
            command += ["-rl", str(self._config.rate_limit)]
        if self._config.retries is not None:
            command += ["-retry", str(self._config.retries)]
        if self._config.http_proxy:
            command += ["-proxy", self._config.http_proxy]
        command += ["-jsonl"]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_katana_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_katana_output(parsed_output)
