"""Nikto plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_nikto_output
from .parser import parse_nikto_output
from .validator import validate_nikto_target

logger = get_plugin_logger("nikto")


class NiktoPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["nikto", "nikto.pl"]
    VERSION_ARGS = ["-Version"]
    VERSION_PATTERN = r"(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_nikto_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "nikto", "-h", context.target_value, *self._config.arguments]
        if self._config.http_proxy:
            command += ["-useproxy", self._config.http_proxy]
        command += ["-Format", "xml", "-o", "-"]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_nikto_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_nikto_output(parsed_output)
