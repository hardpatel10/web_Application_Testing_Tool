"""Output parsing for Subfinder. Its ``-json`` output is JSON-lines."""

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import parse_json_lines


def parse_subfinder_output(raw_output: PluginRawOutput) -> list:
    return parse_json_lines(raw_output.stdout)
