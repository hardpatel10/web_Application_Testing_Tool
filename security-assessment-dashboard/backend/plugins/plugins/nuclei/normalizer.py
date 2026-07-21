"""Normalizes parsed Nuclei output into the platform's common shape.

Produces hosts and observations only — per ``.claude/CLAUDE.md`` and this
phase's explicit instruction, this never generates a `Finding` itself,
even though Nuclei's own JSON output already carries a real severity,
CVE/CWE ids, and a CVSS score. Those are real facts the tool itself
reported (not fabricated or re-derived), so they are folded verbatim into
the observation's ``detail`` as plain, structured text -- the same
"record what the tool said, without judging it further" discipline
``nmap/normalizer.py`` applies to NSE script output and
``nikto/normalizer.py`` applies to OSVDB/CVE references extracted from
Nikto's free text. A Correlation Engine rule can read this text back out
to build an actual scored `Finding` (see
``backend/correlation/rules/cross_tool_rules.py``).
"""

import re
from urllib.parse import urlparse

from backend.models.enums import HostState, ObservationCategory, TargetType
from backend.plugins.models.normalized import NormalizedAddress, NormalizedHost, NormalizedObservation, NormalizedOutput

from .parser import NucleiFinding, NucleiScanResult

_IPV4_PATTERN = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

#: Nuclei tag -> category, checked in order. Neutral grouping metadata only.
_CATEGORY_TAGS: tuple[tuple[tuple[str, ...], ObservationCategory], ...] = (
    (("ssl", "tls"), ObservationCategory.TLS),
    (("exposure", "panel", "config", "misconfig", "default-login"), ObservationCategory.CONFIGURATION),
    (("network", "dns"), ObservationCategory.NETWORK),
)


def _categorize(tags: list[str]) -> ObservationCategory:
    lowered = {tag.lower() for tag in tags}
    for keywords, category in _CATEGORY_TAGS:
        if lowered.intersection(keywords):
            return category
    return ObservationCategory.WEB


def _host_facts(raw_host: str | None, ip: str | None) -> tuple[str | None, str | None]:
    """Reduce Nuclei's ``host``/``ip`` fields to (hostname, ipv4-or-None)."""
    hostname = None
    if raw_host:
        parsed = urlparse(raw_host if "://" in raw_host else f"//{raw_host}")
        hostname = parsed.hostname or raw_host

    ipv4 = ip if ip and _IPV4_PATTERN.match(ip) else None
    if ipv4 is None and hostname and _IPV4_PATTERN.match(hostname):
        ipv4 = hostname
        hostname = None
    return hostname, ipv4


def _finding_detail(finding: NucleiFinding) -> str:
    lines = [f"Severity: {finding.severity}"]
    if finding.cve_ids:
        lines.append(f"CVE: {', '.join(finding.cve_ids)}")
    if finding.cwe_ids:
        lines.append(f"CWE: {', '.join(finding.cwe_ids)}")
    if finding.cvss_score is not None:
        lines.append(f"CVSS: {finding.cvss_score}")
    if finding.description:
        lines.append(f"Description: {finding.description}")
    if finding.matched_at:
        lines.append(f"Matched: {finding.matched_at}")
    if finding.matcher_name:
        lines.append(f"Matcher: {finding.matcher_name}")
    if finding.tags:
        lines.append(f"Tags: {', '.join(finding.tags)}")
    if finding.extracted_results:
        lines.append(f"Extracted: {', '.join(finding.extracted_results)}")
    if finding.reference_urls:
        lines.append(f"References: {', '.join(finding.reference_urls)}")
    return "\n".join(lines)


def normalize_nuclei_output(parsed_output: NucleiScanResult | None) -> NormalizedOutput:
    if parsed_output is None or not parsed_output.findings:
        return NormalizedOutput()

    # Nuclei is only ever pointed at one target per job (like Nikto) -- every finding
    # belongs to the same single host, so this always normalizes to exactly one NormalizedHost.
    first = parsed_output.findings[0]
    hostname, ipv4 = _host_facts(first.host, first.ip)
    addresses = [NormalizedAddress(ip_address=ipv4, version=TargetType.IPV4)] if ipv4 else []

    host = NormalizedHost(
        hostname=hostname,
        fqdn=hostname,
        addresses=addresses,
        state=HostState.UP if (hostname or ipv4) else HostState.UNKNOWN,
    )

    observations = [
        NormalizedObservation(
            source="nuclei",
            title=finding.template_name,
            detail=_finding_detail(finding),
            host_index=0,
            category=_categorize(finding.tags).value,
            observation_type=finding.template_id,
        )
        for finding in parsed_output.findings
    ]

    return NormalizedOutput(hosts=[host], observations=observations)
