"""Output normalization for Dirsearch. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_dirsearch_output(parsed_output) -> dict:
    return {"source_plugin": "dirsearch", "has_output": parsed_output is not None}
