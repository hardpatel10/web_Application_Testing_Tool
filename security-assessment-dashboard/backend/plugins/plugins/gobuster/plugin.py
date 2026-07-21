"""Gobuster plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_gobuster_output
from .parser import parse_gobuster_output
from .validator import validate_gobuster_target

logger = get_plugin_logger("gobuster")


class GobusterPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["gobuster"]
    VERSION_ARGS = ["version"]  # gobuster uses a subcommand, not a flag
    VERSION_PATTERN = r"(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_gobuster_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "gobuster", "dir", "-u", context.target_value]
        wordlist = self._config.wordlists.get("directory")
        if wordlist:
            command += ["-w", str(wordlist)]
        if self._config.retries is not None:
            command += ["-r"] if self._config.retries > 0 else []
        if self._config.http_proxy:
            command += ["-p", self._config.http_proxy]
        command += self._config.arguments
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_gobuster_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_gobuster_output(parsed_output)
