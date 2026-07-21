"""Output parsing for FFUF. Its ``-of json`` output is a single JSON document."""

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import safe_json_loads


def parse_ffuf_output(raw_output: PluginRawOutput):
    return safe_json_loads(raw_output.stdout)
