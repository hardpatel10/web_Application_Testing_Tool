"""Amass plugin: detection, configuration, and command construction only."""

from backend.models.enums import TargetType
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger

from .normalizer import normalize_amass_output
from .parser import parse_amass_output
from .validator import validate_amass_target

logger = get_plugin_logger("amass")


class AmassPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["amass"]
    VERSION_ARGS = ["-version"]
    VERSION_PATTERN = r"v?(\d+\.\d+\.\d+)"

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_amass_target(target_type, target_value)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        command = [str(executable) if executable else "amass", "enum", "-d", context.target_value, *self._config.arguments]
        wordlist = self._config.wordlists.get("subdomains")
        if wordlist:
            command += ["-brute", "-w", str(wordlist)]
        command += ["-json", "-"]
        return command

    def parse(self, raw_output: PluginRawOutput):
        return parse_amass_output(raw_output)

    def normalize(self, parsed_output):
        return normalize_amass_output(parsed_output)
