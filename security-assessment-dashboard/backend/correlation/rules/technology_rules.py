"""Technology Rules: conclusions drawn from ``Technology`` rows (product/version signatures).

No CVE is ever attached here (see ``.claude/CLAUDE.md``'s "never fabricate a
finding"/"references must be real" instructions) -- these rules flag a
*class* of risk (end-of-life software, an exposed administrative interface)
using only a fixed, documented name/version match, backed by CWE/OWASP
references that are genuinely applicable to that class, never a guessed CVE
number for a specific version.
"""

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, RuleCategory

#: name (lowercased, substring match) -> max version prefix considered end-of-life.
#: Deliberately small and conservative: only well-known, unambiguously EOL major lines.
_EOL_TECHNOLOGIES: dict[str, tuple[str, ...]] = {
    "php": ("5.", "7.0", "7.1", "7.2", "7.3"),
    "apache": ("2.2.",),
    "openssl": ("1.0.", "0."),
    "iis": ("6.", "7.0"),
    "mysql": ("5.5", "5.1", "5.0"),
    "nginx": ("1.0.", "1.1.", "1.2.", "1.3.", "1.4.", "1.5.", "1.6.", "1.7.", "1.8.", "1.9."),
}

_ADMIN_INTERFACE_KEYWORDS = ("phpmyadmin", "tomcat manager", "jenkins", "webmin", "pgadmin", "adminer")


class EndOfLifeTechnologyRule(CorrelationRule):
    rule_id = "TECH-001"
    title = "End-of-Life or Unmaintained Software Version Detected"
    description = (
        "A detected product/version matches a known end-of-life release line that no longer "
        "receives security updates from its vendor."
    )
    category = RuleCategory.TECHNOLOGY
    severity = FindingSeverity.HIGH
    base_confidence = FindingConfidence.MEDIUM
    impact = "Unpatched, publicly known vulnerabilities in this release line will never be fixed by the vendor."
    remediation = "Upgrade to a currently supported release, or isolate the component if an upgrade is not immediately possible."
    references = (
        RuleReference(FindingReferenceType.CWE, "CWE-1104"),
        RuleReference(FindingReferenceType.OWASP, "A06:2021"),
    )

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for technology in context.technologies:
            name = technology.name.lower()
            version = (technology.version or "").strip()
            if not version:
                continue
            for known_name, eol_prefixes in _EOL_TECHNOLOGIES.items():
                if known_name not in name:
                    continue
                if any(version.startswith(prefix) for prefix in eol_prefixes):
                    candidates.append(
                        FindingCandidate(
                            detail=f"{technology.name} {technology.version} matches a known end-of-life release line.",
                            evidence_title=f"{technology.name} {technology.version}",
                            matched_technologies=[technology],
                        )
                    )
                break
        return candidates


class AdminInterfaceDetectedRule(CorrelationRule):
    rule_id = "TECH-003"
    title = "Administrative Interface Exposed"
    description = "A well-known administrative or management web interface was detected as reachable."
    category = RuleCategory.TECHNOLOGY
    severity = FindingSeverity.MEDIUM
    base_confidence = FindingConfidence.MEDIUM
    impact = "Administrative interfaces are high-value targets for credential brute-forcing and, if misconfigured, unauthenticated access."
    remediation = "Restrict access to administrative interfaces to trusted networks/VPN and confirm strong authentication is enforced."
    references = (
        RuleReference(FindingReferenceType.CWE, "CWE-16"),
        RuleReference(FindingReferenceType.OWASP, "A05:2021"),
    )

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for technology in context.technologies:
            name = technology.name.lower()
            if any(keyword in name for keyword in _ADMIN_INTERFACE_KEYWORDS):
                candidates.append(
                    FindingCandidate(
                        detail=f"Detected technology '{technology.name}' matches a known administrative interface signature.",
                        evidence_title=technology.name,
                        matched_technologies=[technology],
                    )
                )
        return candidates


RULES: tuple[type[CorrelationRule], ...] = (
    EndOfLifeTechnologyRule,
    AdminInterfaceDetectedRule,
)
