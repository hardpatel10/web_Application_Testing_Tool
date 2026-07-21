"""WhatWeb plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_whatweb_output
from .parser import parse_whatweb_output
from .validator import validate_whatweb_target

logger = get_plugin_logger("whatweb")


class WhatWebPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["whatweb"]
    VERSION_ARGS = ["--version"]
    VERSION_PATTERN = r"(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_whatweb_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "whatweb", *self._config.arguments]
        if self._config.http_proxy:
            command += ["--proxy", self._config.http_proxy]
        command += ["--log-json=-", context.target_value]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_whatweb_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_whatweb_output(parsed_output)
