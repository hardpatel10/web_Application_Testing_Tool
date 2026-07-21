"""FFUF plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_ffuf_output
from .parser import parse_ffuf_output
from .validator import validate_ffuf_target

logger = get_plugin_logger("ffuf")


class FfufPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["ffuf"]
    VERSION_ARGS = ["-V"]
    VERSION_PATTERN = r"([\w.\-]+)$"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_ffuf_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        target_url = context.target_value if "FUZZ" in context.target_value else f"{context.target_value}/FUZZ"
        command = [str(executable) if executable else "ffuf", "-u", target_url]
        wordlist = self._config.wordlists.get("fuzzing")
        if wordlist:
            command += ["-w", str(wordlist)]
        if self._config.rate_limit:
            command += ["-rate", str(self._config.rate_limit)]
        if self._config.http_proxy:
            command += ["-x", self._config.http_proxy]
        command += [*self._config.arguments, "-of", "json", "-o", "-"]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_ffuf_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_ffuf_output(parsed_output)
