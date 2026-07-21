"""HTTP Rules: conclusions drawn from ``http-headers``/``http-title``-style NSE observations.

The missing-header rules only fire when an ``http-headers`` observation
actually exists for the asset (i.e. the scan actually captured the response
headers) -- absence of evidence is never treated as evidence of absence.
"""

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.correlation.text_utils import contains_any
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, RuleCategory


class MissingHstsHeaderRule(CorrelationRule):
    rule_id = "HTTP-001"
    title = "Missing HTTP Strict-Transport-Security Header"
    description = "The response headers captured for this service do not include a Strict-Transport-Security (HSTS) header."
    category = RuleCategory.HTTP
    severity = FindingSeverity.LOW
    base_confidence = FindingConfidence.MEDIUM
    impact = "Without HSTS, a client's initial connection (or a downgrade attempt) can be forced over unencrypted HTTP."
    remediation = "Add a Strict-Transport-Security response header with an appropriate max-age on every HTTPS response."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-319"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for observation in context.observations:
            if observation.source.lower() != "http-headers":
                continue
            if not contains_any(observation.detail, ("strict-transport-security",)):
                candidates.append(
                    FindingCandidate(
                        detail="No Strict-Transport-Security header was present in the captured response headers.",
                        evidence_title=observation.source,
                        matched_observations=[observation],
                    )
                )
        return candidates


class MissingContentSecurityPolicyRule(CorrelationRule):
    rule_id = "HTTP-002"
    title = "Missing Content-Security-Policy Header"
    description = "The response headers captured for this service do not include a Content-Security-Policy header."
    category = RuleCategory.HTTP
    severity = FindingSeverity.LOW
    base_confidence = FindingConfidence.MEDIUM
    impact = "Without a Content-Security-Policy, the browser has no application-level defense-in-depth against cross-site scripting and data-injection attacks."
    remediation = "Define and send a Content-Security-Policy response header appropriate to the application."
    references = (RuleReference(FindingReferenceType.OWASP, "A05:2021"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for observation in context.observations:
            if observation.source.lower() != "http-headers":
                continue
            if not contains_any(observation.detail, ("content-security-policy",)):
                candidates.append(
                    FindingCandidate(
                        detail="No Content-Security-Policy header was present in the captured response headers.",
                        evidence_title=observation.source,
                        matched_observations=[observation],
                    )
                )
        return candidates


class DirectoryListingEnabledRule(CorrelationRule):
    rule_id = "HTTP-003"
    title = "Directory Listing Enabled"
    description = "The web server appears to be serving a directory index ('Index of /') rather than a specific page, as reported by the scanning tool."
    category = RuleCategory.HTTP
    severity = FindingSeverity.MEDIUM
    base_confidence = FindingConfidence.MEDIUM
    impact = "Directory listings can disclose file names, backups, or configuration files that were not meant to be browsable."
    remediation = "Disable directory listing in the web server configuration and add an index page to every browsable directory."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-548"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        candidates: list[FindingCandidate] = []
        for observation in context.observations:
            if observation.source.lower() not in ("http-title", "http-enum"):
                continue
            if contains_any(observation.detail, ("index of /",)) or contains_any(observation.title, ("index of /",)):
                candidates.append(
                    FindingCandidate(
                        detail="A directory index page was detected.",
                        evidence_title=observation.source,
                        matched_observations=[observation],
                    )
                )
        return candidates


RULES: tuple[type[CorrelationRule], ...] = (
    MissingHstsHeaderRule,
    MissingContentSecurityPolicyRule,
    DirectoryListingEnabledRule,
)
