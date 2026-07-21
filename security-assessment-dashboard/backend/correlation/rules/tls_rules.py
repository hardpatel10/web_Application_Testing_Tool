"""TLS Rules: conclusions drawn from ``ssl-cert``/``ssl-enum-ciphers``-style NSE observations."""

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.correlation.text_utils import contains_any, matching
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, RuleCategory

_WEAK_TLS_MARKERS = ("sslv2", "sslv3", "tlsv1.0", "tls 1.0", "rc4", "export", "null", "des-cbc", "md5")


class SelfSignedCertificateRule(CorrelationRule):
    rule_id = "TLS-001"
    title = "Self-Signed TLS Certificate Detected"
    description = "The TLS certificate presented by this service is self-signed rather than issued by a trusted certificate authority."
    category = RuleCategory.TLS
    severity = FindingSeverity.MEDIUM
    base_confidence = FindingConfidence.HIGH
    impact = "Clients cannot cryptographically verify the server's identity, making the connection susceptible to undetected man-in-the-middle interception."
    remediation = "Issue a certificate from a trusted certificate authority (or an internal CA distributed to all clients) instead of a self-signed one."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-295"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [
            o for o in context.observations
            if o.source.lower() == "ssl-cert" and contains_any(o.detail, ("self signed", "self-signed"))
        ]
        if not matches:
            return []
        return [
            FindingCandidate(
                detail="The presented TLS certificate is self-signed.",
                evidence_title="ssl-cert",
                matched_observations=matches,
            )
        ]


class ExpiredCertificateRule(CorrelationRule):
    rule_id = "TLS-002"
    title = "Expired TLS Certificate Detected"
    description = "The TLS certificate presented by this service is reported as expired by the scanning tool's own certificate check."
    category = RuleCategory.TLS
    severity = FindingSeverity.HIGH
    base_confidence = FindingConfidence.HIGH
    impact = "Clients following certificate validation correctly will reject or warn on this connection; clients that don't validate get no expiry protection at all."
    remediation = "Renew the TLS certificate before its expiry date and monitor certificate expiry going forward."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-295"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [
            o for o in context.observations
            if o.source.lower() == "ssl-cert" and contains_any(o.detail, ("expired", "not valid after"))
        ]
        if not matches:
            return []
        return [
            FindingCandidate(
                detail="The presented TLS certificate is expired.",
                evidence_title="ssl-cert",
                matched_observations=matches,
            )
        ]


class WeakTlsProtocolOrCipherRule(CorrelationRule):
    rule_id = "TLS-003"
    title = "Weak TLS Protocol Version or Cipher Suite Supported"
    description = "This service accepts a deprecated TLS/SSL protocol version or a known-weak cipher suite, as reported by the scanning tool's own TLS enumeration."
    category = RuleCategory.TLS
    severity = FindingSeverity.HIGH
    base_confidence = FindingConfidence.MEDIUM
    impact = "Deprecated protocol versions and weak ciphers (e.g. RC4, export-grade, NULL) are vulnerable to known cryptographic attacks that can expose encrypted traffic."
    remediation = "Disable SSLv2/SSLv3/TLS 1.0 and any export/NULL/RC4 cipher suites; support only TLS 1.2+ with modern cipher suites."
    references = (
        RuleReference(FindingReferenceType.CWE, "CWE-327"),
        RuleReference(FindingReferenceType.OWASP, "A02:2021"),
    )

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for observation in context.observations:
            if observation.source.lower() not in ("ssl-enum-ciphers", "ssl-cert"):
                continue
            found = matching(observation.detail, _WEAK_TLS_MARKERS)
            if not found:
                continue
            candidates.append(
                FindingCandidate(
                    detail=f"Weak TLS indicator(s) found: {', '.join(sorted(set(found)))}.",
                    evidence_title=observation.source,
                    matched_observations=[observation],
                )
            )
        return candidates


RULES: tuple[type[CorrelationRule], ...] = (
    SelfSignedCertificateRule,
    ExpiredCertificateRule,
    WeakTlsProtocolOrCipherRule,
)
