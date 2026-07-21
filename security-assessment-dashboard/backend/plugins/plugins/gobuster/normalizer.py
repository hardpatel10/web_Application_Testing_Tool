"""Output normalization for Gobuster. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_gobuster_output(parsed_output: list[str]) -> dict:
    return {"source_plugin": "gobuster", "result_count": len(parsed_output)}
