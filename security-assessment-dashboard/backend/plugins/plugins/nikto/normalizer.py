"""Output normalization for Nikto. Full Finding-schema mapping is a future correlation phase's job."""

from xml.etree.ElementTree import Element


def normalize_nikto_output(parsed_output: Element | None) -> dict:
    return {"source_plugin": "nikto", "has_output": parsed_output is not None}
