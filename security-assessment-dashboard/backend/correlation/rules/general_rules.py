"""General Rules: conclusions that don't fit a specific protocol/technology category."""

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, PortState, RuleCategory


class ServiceVersionDisclosureRule(CorrelationRule):
    rule_id = "GEN-001"
    title = "Detailed Service Version Information Disclosed"
    description = "One or more open services returned a detailed product/version banner during scanning."
    category = RuleCategory.GENERAL
    severity = FindingSeverity.INFO
    base_confidence = FindingConfidence.HIGH
    impact = "Detailed version banners make it easier for an attacker to identify which known vulnerabilities might apply to this host without further probing."
    remediation = "Where practical, suppress or generalize service banners (e.g. remove version strings from HTTP Server headers); this is a defense-in-depth measure, not a substitute for patching."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-200"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [
            service
            for service in context.services
            if service.state == PortState.OPEN and service.product and service.version
        ]
        if not matches:
            return []
        summary = "; ".join(f"{s.product} {s.version} ({s.port}/{s.protocol.value})" for s in matches[:10])
        return [
            FindingCandidate(
                detail=f"Detailed version banners observed: {summary}.",
                evidence_title=f"{len(matches)} service(s) with version banners",
                matched_services=matches,
            )
        ]


RULES: tuple[type[CorrelationRule], ...] = (ServiceVersionDisclosureRule,)
