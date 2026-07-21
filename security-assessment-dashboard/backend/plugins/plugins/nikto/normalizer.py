"""Normalizes parsed Nikto output into the platform's common shape.

Produces hosts and observations only — per ``.claude/CLAUDE.md`` and this
phase's explicit instruction, this never generates a vulnerability, never
assigns a CVSS score, and never fabricates a Finding, even though some of
Nikto's own finding text references a real OSVDB id, CVE, or CWE. Those
references are real facts Nikto itself reported in its text, so they are
extracted (via regex over the finding's own description, never guessed)
and folded into the observation's ``detail`` as plain, neutral text --
exactly the same "record what the tool said, verbatim, without judging
it" discipline ``nmap/normalizer.py`` already follows for NSE script
output. A future Correlation Engine rule can read that text back out
(see ``backend/correlation/rules/``, which already does this kind of
regex extraction over ``Observation.detail`` for other tools).
"""

import re

from backend.models.enums import HostState, ObservationCategory, TargetType
from backend.plugins.models.normalized import NormalizedAddress, NormalizedHost, NormalizedObservation, NormalizedOutput

from .parser import NiktoFinding, NiktoHost, NiktoScanResult

_CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
_CWE_PATTERN = re.compile(r"CWE-\d{1,5}", re.IGNORECASE)

#: Keyword -> category, checked in order against a finding's own description text.
#: Neutral grouping metadata only, not a severity or vulnerability judgment.
_CATEGORY_KEYWORDS: tuple[tuple[tuple[str, ...], ObservationCategory], ...] = (
    (("ssl", "tls", "certificate", "cipher"), ObservationCategory.TLS),
    (("authentication", "auth ", "login", "password", "credential"), ObservationCategory.AUTH),
    (("default file", "default install", "misconfigur", "directory listing", "sample"), ObservationCategory.CONFIGURATION),
)

_IPV4_PATTERN = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def _categorize(description: str) -> ObservationCategory:
    lowered = description.lower()
    for keywords, category in _CATEGORY_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return category
    return ObservationCategory.WEB


def _extract_references(description: str) -> str:
    """Real CVE/CWE ids found in the finding's own text, formatted as extractable facts."""
    cves = sorted(set(_CVE_PATTERN.findall(description)))
    cwes = sorted(set(_CWE_PATTERN.findall(description)))
    lines = []
    if cves:
        lines.append(f"CVE: {', '.join(cve.upper() for cve in cves)}")
    if cwes:
        lines.append(f"CWE: {', '.join(cwe.upper() for cwe in cwes)}")
    return "\n".join(lines)


def _finding_detail(finding: NiktoFinding) -> str:
    parts = [finding.description]
    references = _extract_references(finding.description)
    if references:
        parts.append(references)
    if finding.osvdb_id and finding.osvdb_id != "0":
        parts.append(f"OSVDB: {finding.osvdb_id}")
    if finding.method:
        parts.append(f"Method: {finding.method}")
    if finding.uri:
        parts.append(f"URI: {finding.uri}")
    return "\n".join(parts)


def normalize_nikto_output(parsed_output: NiktoScanResult | None) -> NormalizedOutput:
    if parsed_output is None:
        return NormalizedOutput()

    hosts: list[NormalizedHost] = []
    observations: list[NormalizedObservation] = []

    for index, host in enumerate(parsed_output.hosts):
        hosts.append(_normalize_host(host))
        observations.extend(_normalize_observations(host, host_index=index))

    return NormalizedOutput(hosts=hosts, observations=observations)


def _normalize_host(host: NiktoHost) -> NormalizedHost:
    addresses = []
    if host.target_ip and _IPV4_PATTERN.match(host.target_ip):
        addresses.append(NormalizedAddress(ip_address=host.target_ip, version=TargetType.IPV4))

    return NormalizedHost(
        hostname=host.target_hostname,
        fqdn=host.target_hostname,
        addresses=addresses,
        # Nikto only ever connects to the one target it was pointed at -- it never itself
        # reports host reachability the way an nmap ping/port scan does, so "reached and got
        # an HTTP response" is the only honest reachability fact available here.
        state=HostState.UP if (host.target_ip or host.target_hostname) else HostState.UNKNOWN,
    )


_TITLE_MAX_LENGTH = 120


def _title(finding: NiktoFinding) -> str:
    """A short label for the finding list -- never split on '.', which breaks on version
    numbers and IPs (e.g. "Apache/2.4.49 appears outdated..." would truncate to "Apache/2")."""
    description = finding.description.strip()
    if not description:
        return f"Nikto finding {finding.finding_id}"
    if len(description) <= _TITLE_MAX_LENGTH:
        return description
    return description[:_TITLE_MAX_LENGTH].rsplit(" ", 1)[0] + "…"


def _normalize_observations(host: NiktoHost, *, host_index: int) -> list[NormalizedObservation]:
    port = int(host.target_port) if host.target_port and host.target_port.isdigit() else None
    return [
        NormalizedObservation(
            source="nikto",
            title=_title(finding),
            detail=_finding_detail(finding),
            host_index=host_index,
            port=port,
            category=_categorize(finding.description).value,
            observation_type=f"nikto-{finding.finding_id}" if finding.finding_id else "nikto-finding",
        )
        for finding in host.findings
    ]
