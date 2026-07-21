"""Output normalization for WhatWeb. Full Finding-schema mapping is a future correlation phase's job."""


def normalize_whatweb_output(parsed_output: list) -> dict:
    return {"source_plugin": "whatweb", "result_count": len(parsed_output)}
