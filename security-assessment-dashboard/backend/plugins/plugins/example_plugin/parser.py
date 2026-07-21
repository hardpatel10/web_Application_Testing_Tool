"""Output parsing for the example plugin.

Parses the fixed stdout the plugin's ``execute()`` produces (never a real
tool's output — this plugin never runs a subprocess) into a small
intermediate structure, demonstrating where a real plugin would parse its
tool's actual output format.
"""

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import safe_json_loads


def parse_example_output(raw_output: PluginRawOutput) -> dict:
    """Parse the plugin's raw stdout into an intermediate structure."""
    parsed = safe_json_loads(raw_output.stdout)
    if not isinstance(parsed, dict):
        return {"example": False, "reason": "unparseable output"}
    return parsed
