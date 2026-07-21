"""Output parsing for WhatWeb. Its ``--log-json`` output is a JSON array."""

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import safe_json_loads


def parse_whatweb_output(raw_output: PluginRawOutput) -> list:
    parsed = safe_json_loads(raw_output.stdout)
    return parsed if isinstance(parsed, list) else []
