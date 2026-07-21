"""Output normalization for Subfinder. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_subfinder_output(parsed_output: list) -> dict:
    return {"source_plugin": "subfinder", "result_count": len(parsed_output)}
