"""Output normalization for Naabu. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_naabu_output(parsed_output: list) -> dict:
    return {"source_plugin": "naabu", "result_count": len(parsed_output)}
