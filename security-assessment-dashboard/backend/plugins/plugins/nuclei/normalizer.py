"""Output normalization for Nuclei. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_nuclei_output(parsed_output: list) -> dict:
    return {"source_plugin": "nuclei", "result_count": len(parsed_output)}
