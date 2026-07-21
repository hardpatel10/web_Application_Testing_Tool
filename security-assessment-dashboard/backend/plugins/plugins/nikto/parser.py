"""Output parsing for Nikto. Its ``-Format xml`` output is XML."""

from xml.etree.ElementTree import Element

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import safe_xml_parse


def parse_nikto_output(raw_output: PluginRawOutput) -> Element | None:
    return safe_xml_parse(raw_output.stdout)
