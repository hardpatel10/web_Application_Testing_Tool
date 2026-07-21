"""Output normalization for the dummy execution plugin.

Converts the parser's intermediate structure into the platform's common
shape. This plugin never returns a real finding -- normalization here only
proves the pipeline shape a real plugin would follow.
"""


def normalize_dummy_output(parsed_output: dict) -> dict:
    """Normalize parsed output into the platform's common shape."""
    return {"source_plugin": "dummy-execution", "succeeded": parsed_output.get("exit_code") == 0}
