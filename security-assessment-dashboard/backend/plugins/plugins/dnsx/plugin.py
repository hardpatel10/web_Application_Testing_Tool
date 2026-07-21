"""DNSx plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_dnsx_output
from .parser import parse_dnsx_output
from .validator import validate_dnsx_target

logger = get_plugin_logger("dnsx")


class DnsxPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["dnsx"]
    VERSION_ARGS = ["-version"]
    VERSION_PATTERN = r"v?(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_dnsx_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "dnsx", "-d", context.target_value, *self._config.arguments]
        if self._config.retries is not None:
            command += ["-retry", str(self._config.retries)]
        command += ["-json"]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_dnsx_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_dnsx_output(parsed_output)
