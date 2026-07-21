"""Output parsing for Nuclei. Its ``-jsonl`` output is JSON-lines, one finding per line.

Mirrors ``backend.plugins.plugins.nmap.parser``'s shape: a small, plain
dataclass that only describes what one Nuclei JSON result actually
contains -- no interpretation, scoring, or filtering happens here, only
structural extraction. ``normalizer.py`` is what turns this into
observations.
"""

from dataclasses import dataclass, field
from typing import Any

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import parse_json_lines


@dataclass(frozen=True)
class NucleiFinding:
    """One JSONL result line -- one template match Nuclei reported."""

    template_id: str
    template_name: str
    severity: str
    description: str | None
    protocol: str | None
    host: str | None
    ip: str | None
    matched_at: str | None
    timestamp: str | None
    matcher_name: str | None
    tags: list[str] = field(default_factory=list)
    cve_ids: list[str] = field(default_factory=list)
    cwe_ids: list[str] = field(default_factory=list)
    cvss_score: float | None = None
    reference_urls: list[str] = field(default_factory=list)
    extracted_results: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NucleiScanResult:
    findings: list[NucleiFinding] = field(default_factory=list)


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def parse_nuclei_output(raw_output: PluginRawOutput) -> NucleiScanResult | None:
    """Parse Nuclei's JSONL report. Returns ``None`` if stdout has no output at all.

    Individual malformed lines are skipped by ``parse_json_lines`` rather
    than aborting the whole result -- one bad line shouldn't discard every
    finding a real scan produced.
    """
    if not raw_output.stdout.strip():
        return None

    lines = parse_json_lines(raw_output.stdout)
    findings = [_parse_finding(line) for line in lines if isinstance(line, dict)]
    return NucleiScanResult(findings=[f for f in findings if f is not None])


def _parse_finding(line: dict) -> NucleiFinding | None:
    info = line.get("info") or {}
    if not isinstance(info, dict):
        info = {}
    classification = info.get("classification") or {}
    if not isinstance(classification, dict):
        classification = {}

    template_id = line.get("template-id") or line.get("templateID")
    if not template_id:
        return None

    return NucleiFinding(
        template_id=str(template_id),
        template_name=str(info.get("name") or template_id),
        severity=str(info.get("severity") or "unknown").lower(),
        description=info.get("description"),
        protocol=line.get("type"),
        host=line.get("host"),
        ip=line.get("ip"),
        matched_at=line.get("matched-at") or line.get("matched"),
        timestamp=line.get("timestamp"),
        matcher_name=line.get("matcher-name"),
        tags=[str(tag) for tag in _as_list(info.get("tags"))],
        cve_ids=[str(cve).upper() for cve in _as_list(classification.get("cve-id"))],
        cwe_ids=[str(cwe).upper() for cwe in _as_list(classification.get("cwe-id"))],
        cvss_score=_safe_float(classification.get("cvss-score")),
        reference_urls=[str(ref) for ref in _as_list(info.get("reference"))],
        extracted_results=[str(item) for item in _as_list(line.get("extracted-results"))],
    )


def _safe_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
