"""Output parsing for Naabu. Its ``-json`` output is JSON-lines."""

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import parse_json_lines


def parse_naabu_output(raw_output: PluginRawOutput) -> list:
    return parse_json_lines(raw_output.stdout)
