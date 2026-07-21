"""Protocol Rules: conclusions drawn from protocol-level NSE script observations.

Both rules here key off a script that, by Nmap's own design, only writes
output when the risky condition is actually true (a successful zone
transfer, a readable SNMP community string) -- the observation's mere
*presence* is the deterministic signal, not a text-content guess.
"""

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, RuleCategory


class DnsZoneTransferAllowedRule(CorrelationRule):
    rule_id = "PROTO-002"
    title = "DNS Zone Transfer Allowed"
    description = "A DNS zone transfer (AXFR) against this host succeeded, as reported by the scanning tool's own zone-transfer check."
    category = RuleCategory.PROTOCOL
    severity = FindingSeverity.HIGH
    base_confidence = FindingConfidence.HIGH
    impact = "A successful zone transfer discloses the full DNS record set for the zone, including internal hostnames that were not intended to be public."
    remediation = "Restrict zone transfers (AXFR) to authorized secondary name servers only."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-200"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [o for o in context.observations if o.source.lower() == "dns-zone-transfer"]
        if not matches:
            return []
        return [
            FindingCandidate(
                detail="A DNS zone transfer succeeded against this host.",
                evidence_title="dns-zone-transfer",
                matched_observations=matches,
            )
        ]


class SnmpDefaultCommunityStringRule(CorrelationRule):
    rule_id = "PROTO-001"
    title = "SNMP Reachable With a Guessable Community String"
    description = "SNMP responded to a request using a common/default community string, as reported by the scanning tool's own SNMP check."
    category = RuleCategory.PROTOCOL
    severity = FindingSeverity.HIGH
    base_confidence = FindingConfidence.HIGH
    impact = "SNMP with a default community string frequently discloses system, interface, and routing information, and on some devices allows write access to device configuration."
    remediation = "Disable SNMP if unused, or set unique, non-default community strings (or move to SNMPv3 with authentication/encryption) and restrict SNMP to management hosts only."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-521"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [o for o in context.observations if o.source.lower() in ("snmp-info", "snmp-sysdescr")]
        if not matches:
            return []
        return [
            FindingCandidate(
                detail="SNMP responded using a guessable community string.",
                evidence_title=matches[0].source,
                matched_observations=matches,
            )
        ]


RULES: tuple[type[CorrelationRule], ...] = (
    DnsZoneTransferAllowedRule,
    SnmpDefaultCommunityStringRule,
)
