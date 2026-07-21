"""Output normalization for SSLScan. Full Finding-schema mapping is a future correlation phase's job."""

from xml.etree.ElementTree import Element


def normalize_sslscan_output(parsed_output: Element | None) -> dict:
    return {"source_plugin": "sslscan", "has_output": parsed_output is not None}
