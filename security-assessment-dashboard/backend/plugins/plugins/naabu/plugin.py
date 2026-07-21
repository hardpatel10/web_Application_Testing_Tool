"""Naabu plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_naabu_output
from .parser import parse_naabu_output
from .validator import validate_naabu_target

logger = get_plugin_logger("naabu")


class NaabuPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["naabu"]
    VERSION_ARGS = ["-version"]
    VERSION_PATTERN = r"v?(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_naabu_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "naabu", "-host", context.target_value, *self._config.arguments]
        if self._config.rate_limit:
            command += ["-rate", str(self._config.rate_limit)]
        if self._config.retries is not None:
            command += ["-retries", str(self._config.retries)]
        command += ["-json"]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_naabu_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_naabu_output(parsed_output)
