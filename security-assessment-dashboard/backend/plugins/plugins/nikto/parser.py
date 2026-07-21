"""Output parsing for Nikto. Its ``-Format xml -o -`` output is XML on stdout.

Mirrors ``backend.plugins.plugins.nmap.parser``'s shape: small, plain
dataclasses that only describe what Nikto's XML report actually contains
-- no interpretation, scoring, or filtering happens here, only structural
extraction. ``normalizer.py`` is what turns this into observations.
"""

from dataclasses import dataclass, field

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import safe_xml_parse


@dataclass(frozen=True)
class NiktoFinding:
    """One ``<item>`` element -- one thing Nikto's checks flagged about the target."""

    finding_id: str
    osvdb_id: str | None
    method: str | None
    description: str
    uri: str | None
    name_link: str | None
    ip_link: str | None


@dataclass(frozen=True)
class NiktoHost:
    """One ``<scandetails>`` element -- the target Nikto actually connected to."""

    target_ip: str | None
    target_hostname: str | None
    target_port: str | None
    findings: list[NiktoFinding] = field(default_factory=list)


@dataclass(frozen=True)
class NiktoScanResult:
    hosts: list[NiktoHost] = field(default_factory=list)


def parse_nikto_output(raw_output: PluginRawOutput) -> NiktoScanResult | None:
    """Parse Nikto's XML report. Returns ``None`` if the output isn't parseable XML."""
    root = safe_xml_parse(raw_output.stdout)
    if root is None:
        return None

    hosts: list[NiktoHost] = []
    for scandetails in root.iter("scandetails"):
        findings = [
            NiktoFinding(
                finding_id=item.get("id", ""),
                osvdb_id=item.get("osvdbid") or None,
                method=item.get("method") or None,
                description=(item.findtext("description") or "").strip(),
                uri=(item.findtext("uri") or None),
                name_link=(item.findtext("namelink") or None),
                ip_link=(item.findtext("iplink") or None),
            )
            for item in scandetails.findall("item")
        ]
        hosts.append(
            NiktoHost(
                target_ip=scandetails.get("targetip") or None,
                target_hostname=scandetails.get("targethostname") or None,
                target_port=scandetails.get("targetport") or None,
                findings=findings,
            )
        )
    return NiktoScanResult(hosts=hosts)
