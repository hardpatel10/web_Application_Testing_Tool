"""Dirsearch plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_dirsearch_output
from .parser import parse_dirsearch_output
from .validator import validate_dirsearch_target

logger = get_plugin_logger("dirsearch")


class DirsearchPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["dirsearch"]
    VERSION_ARGS = ["--version"]
    VERSION_PATTERN = r"(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_dirsearch_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "dirsearch", "-u", context.target_value]
        wordlist = self._config.wordlists.get("directory")
        if wordlist:
            command += ["-w", str(wordlist)]
        if self._config.retries is not None:
            command += ["--max-retries", str(self._config.retries)]
        if self._config.http_proxy:
            command += ["--proxy", self._config.http_proxy]
        command += [*self._config.arguments, "--format", "json", "-o", "-"]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_dirsearch_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_dirsearch_output(parsed_output)
