"""Output normalization for the example plugin.

Converts the parser's intermediate structure into the shape the platform
would eventually correlate/store as findings. This plugin never returns a
real finding — normalization here only proves the pipeline shape a real
plugin would follow.
"""


def normalize_example_output(parsed_output: dict) -> dict:
    """Normalize parsed output into the platform's common shape."""
    return {
        "source_plugin": "example-plugin",
        "verified_framework_pipeline": bool(parsed_output.get("example")),
    }
