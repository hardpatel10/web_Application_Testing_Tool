"""Output parsing for Gobuster. Plain-text, one result per line."""

from backend.plugins.models.execution import PluginRawOutput


def parse_gobuster_output(raw_output: PluginRawOutput) -> list[str]:
    return [line.strip() for line in raw_output.stdout.splitlines() if line.strip()]
