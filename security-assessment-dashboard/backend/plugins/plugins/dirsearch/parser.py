"""Output parsing for Dirsearch. Its ``--format json`` output is a JSON document."""

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import safe_json_loads


def parse_dirsearch_output(raw_output: PluginRawOutput):
    return safe_json_loads(raw_output.stdout)
