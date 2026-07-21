"""Feroxbuster plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_feroxbuster_output
from .parser import parse_feroxbuster_output
from .validator import validate_feroxbuster_target

logger = get_plugin_logger("feroxbuster")


class FeroxbusterPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["feroxbuster"]
    VERSION_ARGS = ["--version"]
    VERSION_PATTERN = r"(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_feroxbuster_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "feroxbuster", "-u", context.target_value]
        wordlist = self._config.wordlists.get("directory")
        if wordlist:
            command += ["-w", str(wordlist)]
        if self._config.rate_limit:
            command += ["--rate-limit", str(self._config.rate_limit)]
        if self._config.retries is not None:
            command += ["--retries", str(self._config.retries)]
        if self._config.http_proxy:
            command += ["--proxy", self._config.http_proxy]
        command += [*self._config.arguments, "--json"]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_feroxbuster_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_feroxbuster_output(parsed_output)
