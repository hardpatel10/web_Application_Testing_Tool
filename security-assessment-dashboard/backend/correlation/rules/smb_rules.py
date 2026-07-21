"""SMB Rules: conclusions drawn from ``smb-security-mode``/``smb2-security-mode``-style NSE observations."""

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.correlation.text_utils import contains_any
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, RuleCategory


class SmbSigningDisabledRule(CorrelationRule):
    rule_id = "SMB-001"
    title = "SMB Message Signing Disabled"
    description = "SMB message signing is not required by this server, as reported by the scanning tool's own SMB security-mode check."
    category = RuleCategory.SMB
    severity = FindingSeverity.MEDIUM
    base_confidence = FindingConfidence.MEDIUM
    impact = "Without required signing, SMB traffic is more susceptible to relay and man-in-the-middle attacks."
    remediation = "Enable and require SMB signing on this server (and on domain controllers, where it should be mandatory)."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-306"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for observation in context.observations:
            if observation.source.lower() not in ("smb-security-mode", "smb2-security-mode"):
                continue
            if contains_any(observation.detail, ("signing: disabled", "message signing disabled", "signing enabled: false")):
                candidates.append(
                    FindingCandidate(
                        detail="SMB message signing is disabled/not required.",
                        evidence_title=observation.source,
                        matched_observations=[observation],
                    )
                )
        return candidates


class Smbv1EnabledRule(CorrelationRule):
    rule_id = "SMB-002"
    title = "SMBv1 Protocol Enabled"
    description = "This server supports the deprecated SMBv1 protocol, as reported by the scanning tool's own SMB protocol check."
    category = RuleCategory.SMB
    severity = FindingSeverity.HIGH
    base_confidence = FindingConfidence.MEDIUM
    impact = "SMBv1 has multiple publicly known, severe vulnerabilities and should not be enabled on any network-reachable host."
    remediation = "Disable SMBv1 support entirely; use SMBv2/SMBv3 only."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-1104"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for observation in context.observations:
            if observation.source.lower() not in ("smb-protocols", "smb2-security-mode"):
                continue
            if contains_any(observation.detail, ("smbv1: true", "smbv1 supported", "1.0 (smbv1)")):
                candidates.append(
                    FindingCandidate(
                        detail="SMBv1 support is enabled on this server.",
                        evidence_title=observation.source,
                        matched_observations=[observation],
                    )
                )
        return candidates


RULES: tuple[type[CorrelationRule], ...] = (
    SmbSigningDisabledRule,
    Smbv1EnabledRule,
)
