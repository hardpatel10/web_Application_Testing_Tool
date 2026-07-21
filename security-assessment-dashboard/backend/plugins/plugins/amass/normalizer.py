"""Output normalization for Amass. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_amass_output(parsed_output: list) -> dict:
    return {"source_plugin": "amass", "result_count": len(parsed_output)}
