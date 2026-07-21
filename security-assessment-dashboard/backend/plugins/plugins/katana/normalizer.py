"""Output normalization for Katana. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_katana_output(parsed_output: list) -> dict:
    return {"source_plugin": "katana", "result_count": len(parsed_output)}
