"""XML helpers for plugin output parsers.

Uses ``defusedxml`` rather than the standard library's ``xml.etree``
directly: this dashboard's plugins parse XML *produced by security tools
scanning untrusted targets* (e.g. a hostile server's response reflected
into an XML report), so the parser itself must not be exploitable via
XXE/entity-expansion attacks. Python's own documentation flags
``xml.etree.ElementTree`` as unsafe against maliciously crafted input for
exactly this reason.
"""

from xml.etree.ElementTree import Element  # noqa: S405 - type only, parsing goes through defusedxml below

from defusedxml import ElementTree as _SafeElementTree
from defusedxml.common import DefusedXmlException


def safe_xml_parse(text: str) -> Element | None:
    """Parse ``text`` as XML, returning ``None`` on any parse or entity-expansion error."""
    try:
        return _SafeElementTree.fromstring(text)
    except (DefusedXmlException, SyntaxError, ValueError):
        return None
