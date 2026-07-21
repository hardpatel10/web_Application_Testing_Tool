"""Cross-Tool Rules: a Finding supported by evidence from more than one scanning tool.

Every other rule module reads ``context.observations``/``.technologies``
without caring which tool produced them. These rules are the first to
deliberately branch on ``Observation.plugin`` (the originating tool,
denormalized onto every row at persist time -- see
``backend.services.host_inventory_service``) specifically to combine
signals from *different* tools into one Finding, per this phase's own
worked example:

    Nmap (Apache 2.4.49 fingerprinted) -> Nikto (Server header observed)
    -> Nuclei (CVE-2021-41773 template match) -> ONE Finding, evidence
    from all three tools.

Neither rule here ever invents a CVE. ``MultiToolConfirmedCveRule`` only
fires when the *same* CVE identifier already appears, verbatim, in real
output text from two or more distinct tools (a regex extraction over text
the tools themselves wrote, the same "extract, never guess" discipline
``nikto/normalizer.py``/``nuclei/normalizer.py`` already apply).
``KnownVulnerableTechnologyConfirmedByTemplateRule`` uses a small, static
product/version -> CVE table (the same pattern ``technology_rules.py``'s
``EndOfLifeTechnologyRule`` already uses for EOL software) purely to
*explain* which known-vulnerable pattern matched -- it never cites that
CVE in a Finding unless a template-based scan (Nuclei) has *already, live,
independently* confirmed that exact CVE against the same host. The table
is corroboration labeling, not the source of truth for the vulnerability
claim; the live confirmation is.
"""

import re

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, RuleCategory

_CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)

#: (product name substring, version prefix) -> the specific, real, documented CVE that
#: version line is known to be vulnerable to. Deliberately tiny -- each entry is a
#: well-known, unambiguous public CVE, not a guess about which versions might be affected.
_KNOWN_VULNERABLE_VERSIONS: tuple[tuple[str, str, str], ...] = (
    ("apache", "2.4.49", "CVE-2021-41773"),
    ("apache", "2.4.50", "CVE-2021-42013"),
)


class MultiToolConfirmedCveRule(CorrelationRule):
    rule_id = "CROSS-001"
    title = "Same CVE Independently Reported by Multiple Tools"
    description = (
        "A specific CVE identifier appears in real output text from more than one distinct "
        "scanning tool against the same host, corroborating the finding independently rather "
        "than relying on a single tool's report."
    )
    category = RuleCategory.GENERAL
    severity = FindingSeverity.HIGH
    base_confidence = FindingConfidence.HIGH
    impact = "Independent corroboration across tools substantially reduces the chance of a false positive from any single scanner."
    remediation = "Review the referenced CVE and apply the vendor's fix or documented mitigation."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-1035"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        by_cve: dict[str, list] = {}
        for observation in context.observations:
            if not observation.detail:
                continue
            for cve in {match.upper() for match in _CVE_PATTERN.findall(observation.detail)}:
                by_cve.setdefault(cve, []).append(observation)

        candidates: list[FindingCandidate] = []
        for cve, observations in sorted(by_cve.items()):
            plugins = sorted({observation.plugin for observation in observations if observation.plugin})
            if len(plugins) < 2:
                continue
            candidates.append(
                FindingCandidate(
                    detail=f"{cve} is independently reported in observations from {' and '.join(plugins)} against this host.",
                    evidence_title=cve,
                    title_override=f"{cve} corroborated by {len(plugins)} tools",
                    matched_observations=observations,
                )
            )
        return candidates


class KnownVulnerableTechnologyConfirmedByTemplateRule(CorrelationRule):
    rule_id = "CROSS-002"
    title = "Known-Vulnerable Software Version Confirmed by Template-Based Scan"
    description = (
        "A software product/version fingerprinted by one tool matches a documented "
        "known-vulnerable release, and a template-based scanner (Nuclei) independently "
        "confirmed that exact CVE against the same host."
    )
    category = RuleCategory.GENERAL
    severity = FindingSeverity.CRITICAL
    base_confidence = FindingConfidence.HIGH
    impact = "The affected version is confirmed both by fingerprinting and by a live, template-based proof of the specific vulnerability, not a version match alone."
    remediation = "Upgrade the affected software past the vulnerable version per the vendor's advisory for the referenced CVE."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-1035"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for technology in context.technologies:
            name = technology.name.lower()
            version = (technology.version or "").strip()
            if not version:
                continue
            for known_name, known_version_prefix, cve in _KNOWN_VULNERABLE_VERSIONS:
                if known_name not in name or not version.startswith(known_version_prefix):
                    continue

                confirming = [
                    observation
                    for observation in context.observations
                    if observation.plugin == "nuclei" and observation.detail and cve in observation.detail.upper()
                ]
                if not confirming:
                    # No live template confirmation -- do not cite this CVE from the version match alone.
                    continue

                supporting = [
                    observation
                    for observation in context.observations
                    if observation.plugin not in ("nuclei", None)
                    and observation.detail
                    and (known_name in observation.detail.lower() or known_version_prefix in observation.detail)
                ]

                candidates.append(
                    FindingCandidate(
                        detail=(
                            f"{technology.name} {technology.version} matches the known-vulnerable version for "
                            f"{cve}, independently confirmed by a template-based scan."
                        ),
                        evidence_title=cve,
                        title_override=f"{technology.name} {technology.version} vulnerable to {cve} (confirmed)",
                        matched_technologies=[technology],
                        matched_observations=confirming + supporting,
                    )
                )
        return candidates


RULES: tuple[type[CorrelationRule], ...] = (
    MultiToolConfirmedCveRule,
    KnownVulnerableTechnologyConfirmedByTemplateRule,
)
