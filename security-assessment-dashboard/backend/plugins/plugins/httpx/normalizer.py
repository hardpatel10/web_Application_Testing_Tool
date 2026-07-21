"""Output normalization for HTTPX. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_httpx_output(parsed_output: list) -> dict:
    return {"source_plugin": "httpx", "result_count": len(parsed_output)}
