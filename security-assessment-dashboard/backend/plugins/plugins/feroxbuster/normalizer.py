"""Output normalization for Feroxbuster. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_feroxbuster_output(parsed_output: list) -> dict:
    return {"source_plugin": "feroxbuster", "result_count": len(parsed_output)}
