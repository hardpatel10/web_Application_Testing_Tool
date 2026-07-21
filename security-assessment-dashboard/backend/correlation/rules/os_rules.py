"""Operating System Rules: conclusions drawn from an asset's ``OperatingSystem`` candidates.

Only ever evaluates the single highest-``accuracy`` candidate for an asset --
Nmap OS fingerprinting returns many low-confidence guesses (see Phase 8's
own decision to keep every candidate rather than just the best one); firing
a finding off a 20%-accuracy guess would not be a deterministic, evidence-backed
conclusion.
"""

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, RuleCategory

#: Substring match against OperatingSystem.name, lowercased. Deliberately
#: limited to unambiguously, publicly end-of-life OS families/releases.
_EOL_OS_KEYWORDS = (
    "windows xp", "windows vista", "windows 2000", "windows server 2003",
    "windows server 2008 sp", "windows 7", "windows server 2008 r2",
    "centos 6", "centos linux 6", "ubuntu 14.04", "ubuntu 16.04", "debian 7", "debian 8",
)

#: Minimum OS-match accuracy (Nmap's own 0-100 confidence score) before a
#: candidate is trusted enough to base a finding on.
_MIN_ACCURACY = 85


class EndOfLifeOperatingSystemRule(CorrelationRule):
    rule_id = "OS-001"
    title = "End-of-Life Operating System Detected"
    description = (
        "The asset's highest-confidence OS fingerprint matches an operating system release that "
        "has reached end of support and no longer receives security updates from its vendor."
    )
    category = RuleCategory.OPERATING_SYSTEM
    severity = FindingSeverity.HIGH
    base_confidence = FindingConfidence.MEDIUM
    impact = "Unpatched, publicly known operating-system vulnerabilities will never be fixed by the vendor."
    remediation = "Plan migration to a currently supported operating system release; isolate the host on a restricted network segment until it can be upgraded or decommissioned."
    references = (
        RuleReference(FindingReferenceType.CWE, "CWE-1104"),
        RuleReference(FindingReferenceType.OWASP, "A06:2021"),
    )

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        if not context.operating_systems:
            return []
        best = max(context.operating_systems, key=lambda os: os.accuracy)
        if best.accuracy < _MIN_ACCURACY:
            return []
        name = best.name.lower()
        if not any(keyword in name for keyword in _EOL_OS_KEYWORDS):
            return []
        return [
            FindingCandidate(
                detail=f"Highest-confidence OS match: '{best.name}' ({best.accuracy}% accuracy, source: {best.source}).",
                evidence_title=f"{best.name} ({best.accuracy}% accuracy)",
                matched_operating_systems=[best],
            )
        ]


RULES: tuple[type[CorrelationRule], ...] = (EndOfLifeOperatingSystemRule,)
