"""SSH Rules: conclusions drawn from ``ssh2-enum-algos``/``ssh-hostkey``-style NSE observations.

The phase brief's own worked example ("Weak SSH Algorithms -> Finding,
supported by Nmap Observation + SSH Observation + Evidence") maps directly
to :class:`WeakSshAlgorithmsRule`.
"""

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.correlation.text_utils import matching
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, RuleCategory

_WEAK_SSH_ALGORITHMS = (
    "diffie-hellman-group1-sha1",
    "diffie-hellman-group14-sha1",
    "arcfour",
    "arcfour128",
    "arcfour256",
    "cbc",
    "hmac-md5",
    "hmac-sha1-96",
    "ssh-dss",
)


class WeakSshAlgorithmsRule(CorrelationRule):
    rule_id = "SSH-001"
    title = "Weak SSH Key Exchange, Cipher, or MAC Algorithms Supported"
    description = "The SSH server offers one or more deprecated/weak key exchange, encryption, or message-authentication algorithms, as reported by the scanning tool's own SSH algorithm enumeration."
    category = RuleCategory.SSH
    severity = FindingSeverity.MEDIUM
    base_confidence = FindingConfidence.MEDIUM
    impact = "Weak algorithms reduce the cryptographic strength of the SSH session and, in some cases, are subject to known practical attacks."
    remediation = "Disable weak key exchange algorithms, CBC-mode ciphers, arcfour ciphers, and MD5/96-bit HMACs in the SSH server configuration; keep only modern, strong algorithms."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-327"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for observation in context.observations:
            if observation.source.lower() != "ssh2-enum-algos":
                continue
            found = matching(observation.detail, _WEAK_SSH_ALGORITHMS)
            if not found:
                continue
            candidates.append(
                FindingCandidate(
                    detail=f"Weak SSH algorithm(s) offered: {', '.join(sorted(set(found)))}.",
                    evidence_title=observation.source,
                    matched_observations=[observation],
                )
            )
        return candidates


class SshProtocolVersion1Rule(CorrelationRule):
    rule_id = "SSH-002"
    title = "SSH Protocol Version 1 Supported"
    description = "The SSH server supports the obsolete, cryptographically broken SSH protocol version 1."
    category = RuleCategory.SSH
    severity = FindingSeverity.CRITICAL
    base_confidence = FindingConfidence.HIGH
    impact = "SSH-1 has multiple known cryptographic weaknesses, including susceptibility to man-in-the-middle attacks."
    remediation = "Disable SSH protocol version 1 support entirely; allow only protocol version 2."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-327"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for observation in context.observations:
            if observation.source.lower() not in ("ssh-hostkey", "banner"):
                continue
            if observation.detail and "ssh-1." in observation.detail.lower():
                candidates.append(
                    FindingCandidate(
                        detail="Server banner/host key indicates SSH protocol version 1 support.",
                        evidence_title=observation.source,
                        matched_observations=[observation],
                    )
                )
        return candidates


RULES: tuple[type[CorrelationRule], ...] = (
    WeakSshAlgorithmsRule,
    SshProtocolVersion1Rule,
)
