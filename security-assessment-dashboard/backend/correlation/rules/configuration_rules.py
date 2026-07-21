"""Configuration Rules: conclusions about how a host/service is configured, not any single protocol."""

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, PortState, RuleCategory
from backend.correlation.text_utils import contains_any

#: A large, deliberately conservative default so this only fires on a
#: genuinely broad exposed surface, not routine multi-service hosts.
_LARGE_ATTACK_SURFACE_THRESHOLD = 8


class AnonymousFtpLoginRule(CorrelationRule):
    rule_id = "CONFIG-001"
    title = "Anonymous FTP Login Allowed"
    description = "The FTP service accepted an anonymous login, as reported by the scanning tool's own FTP check."
    category = RuleCategory.CONFIGURATION
    severity = FindingSeverity.CRITICAL
    base_confidence = FindingConfidence.HIGH
    impact = "Anyone can browse (and, depending on permissions, upload or download) files on this FTP server without credentials."
    remediation = "Disable anonymous FTP access unless it is an explicit, intended public file drop with no sensitive content."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-284"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [
            o for o in context.observations
            if o.source.lower() == "ftp-anon" and contains_any(o.detail, ("anonymous ftp login allowed",))
        ]
        if not matches:
            return []
        return [
            FindingCandidate(
                detail="Anonymous FTP login was accepted by the server.",
                evidence_title="ftp-anon",
                matched_observations=matches,
            )
        ]


class LargeAttackSurfaceRule(CorrelationRule):
    rule_id = "CONFIG-002"
    title = "Large Number of Open Ports on a Single Host"
    description = "This host has an unusually large number of distinct open ports, indicating a broad network-exposed attack surface."
    category = RuleCategory.CONFIGURATION
    severity = FindingSeverity.INFO
    base_confidence = FindingConfidence.HIGH
    impact = "Each open service is an additional potential entry point; a large exposed surface is more likely to include a misconfigured or forgotten service."
    remediation = "Review whether every open port is intentional and required; disable or firewall services that are not needed from this network."
    references = (RuleReference(FindingReferenceType.OWASP, "A05:2021"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        open_services = [s for s in context.services if s.state == PortState.OPEN]
        distinct_ports = {(s.port, s.protocol) for s in open_services}
        if len(distinct_ports) < _LARGE_ATTACK_SURFACE_THRESHOLD:
            return []
        return [
            FindingCandidate(
                detail=f"{len(distinct_ports)} distinct open ports were detected on this host.",
                evidence_title=f"{len(distinct_ports)} open ports",
                matched_services=open_services,
            )
        ]


RULES: tuple[type[CorrelationRule], ...] = (
    AnonymousFtpLoginRule,
    LargeAttackSurfaceRule,
)
