"""HTTPX plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_httpx_output
from .parser import parse_httpx_output
from .validator import validate_httpx_target

logger = get_plugin_logger("httpx")


class HttpxPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["httpx"]
    VERSION_ARGS = ["-version"]
    VERSION_PATTERN = r"v?(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_httpx_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "httpx", "-u", context.target_value, *self._config.arguments]
        if self._config.retries is not None:
            command += ["-retries", str(self._config.retries)]
        if self._config.http_proxy:
            command += ["-http-proxy", self._config.http_proxy]
        command += ["-json"]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_httpx_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_httpx_output(parsed_output)
