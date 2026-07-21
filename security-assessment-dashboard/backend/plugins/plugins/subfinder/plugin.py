"""Subfinder plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_subfinder_output
from .parser import parse_subfinder_output
from .validator import validate_subfinder_target

logger = get_plugin_logger("subfinder")


class SubfinderPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["subfinder"]
    VERSION_ARGS = ["-version"]
    VERSION_PATTERN = r"v?(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_subfinder_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "subfinder", "-d", context.target_value, *self._config.arguments]
        if self._config.rate_limit:
            command += ["-rate-limit", str(self._config.rate_limit)]
        if self._config.http_proxy:
            command += ["-proxy", self._config.http_proxy]
        command += ["-json"]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_subfinder_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_subfinder_output(parsed_output)
