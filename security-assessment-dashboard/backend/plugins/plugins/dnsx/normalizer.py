"""Output normalization for DNSx. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_dnsx_output(parsed_output: list) -> dict:
    return {"source_plugin": "dnsx", "result_count": len(parsed_output)}
