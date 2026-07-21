"""Output parsing for the dummy execution plugin.

Parses the plugin's own fixed stdout (never a real tool's output -- this
plugin never runs a subprocess) into a small intermediate structure,
mirroring the shape a real plugin's parser would produce.
"""

from backend.plugins.models.execution import PluginRawOutput


def parse_dummy_output(raw_output: PluginRawOutput) -> dict:
    """Parse the plugin's simulated stdout into an intermediate structure."""
    return {"stdout": raw_output.stdout, "stderr": raw_output.stderr, "exit_code": raw_output.exit_code}
