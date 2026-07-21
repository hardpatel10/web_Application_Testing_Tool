"""Output normalization for FFUF. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_ffuf_output(parsed_output) -> dict:
    return {"source_plugin": "ffuf", "has_output": parsed_output is not None}
