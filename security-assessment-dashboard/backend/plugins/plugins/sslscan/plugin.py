"""SSLScan plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_sslscan_output
from .parser import parse_sslscan_output
from .validator import validate_sslscan_target

logger = get_plugin_logger("sslscan")


class SslscanPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["sslscan"]
    VERSION_ARGS = ["--version"]
    VERSION_PATTERN = r"(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_sslscan_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "sslscan", *self._config.arguments, "--xml=-", context.target_value]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_sslscan_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_sslscan_output(parsed_output)
