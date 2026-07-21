"""Service Rules: conclusions drawn purely from open ``Service`` rows -- no NSE script required.

The one rule category guaranteed to have data to evaluate against on every
completed Nmap scan that does port/service detection, since ``Service`` is
populated regardless of which (if any) NSE scripts ran.
"""

from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, PortState, RuleCategory


def _open(context: RuleContext) -> list:
    return [s for s in context.services if s.state == PortState.OPEN]


class TelnetServiceExposedRule(CorrelationRule):
    rule_id = "SVC-001"
    title = "Telnet Service Exposed"
    description = (
        "An open Telnet service was detected. Telnet transmits credentials and session data "
        "in cleartext and provides no transport encryption."
    )
    category = RuleCategory.SERVICE
    severity = FindingSeverity.HIGH
    base_confidence = FindingConfidence.HIGH
    impact = (
        "Credentials and session traffic exchanged with this service can be captured by anyone "
        "able to observe network traffic to the host."
    )
    remediation = (
        "Disable Telnet and replace it with SSH or another encrypted management protocol. If it "
        "must remain for legacy equipment, restrict access to a dedicated management network."
    )
    references = (
        RuleReference(FindingReferenceType.CWE, "CWE-319"),
        RuleReference(FindingReferenceType.OWASP, "A02:2021"),
    )

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [s for s in _open(context) if s.port == 23 or (s.service_name or "").lower() == "telnet"]
        if not matches:
            return []
        service = matches[0]
        return [
            FindingCandidate(
                detail=f"Telnet service open on port {service.port}/{service.protocol.value}.",
                evidence_title=f"Open port {service.port}/{service.protocol.value} ({service.service_name})",
                matched_services=matches,
            )
        ]


class FtpServiceExposedRule(CorrelationRule):
    rule_id = "SVC-002"
    title = "FTP Service Exposed"
    description = (
        "An open FTP service was detected. Standard FTP transmits credentials and file contents "
        "in cleartext."
    )
    category = RuleCategory.SERVICE
    severity = FindingSeverity.MEDIUM
    base_confidence = FindingConfidence.HIGH
    impact = "Credentials and transferred files can be captured by anyone able to observe network traffic to the host."
    remediation = "Replace FTP with SFTP/FTPS, or restrict access to a trusted management network if it must remain."
    references = (
        RuleReference(FindingReferenceType.CWE, "CWE-319"),
        RuleReference(FindingReferenceType.OWASP, "A02:2021"),
    )

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [s for s in _open(context) if s.port == 21 or (s.service_name or "").lower() == "ftp"]
        if not matches:
            return []
        service = matches[0]
        return [
            FindingCandidate(
                detail=f"FTP service open on port {service.port}/{service.protocol.value}.",
                evidence_title=f"Open port {service.port}/{service.protocol.value} ({service.service_name})",
                matched_services=matches,
            )
        ]


class SmbServiceExposedRule(CorrelationRule):
    rule_id = "SVC-003"
    title = "SMB Service Exposed to the Network"
    description = "An open SMB/CIFS file-sharing service was detected on the standard SMB port(s)."
    category = RuleCategory.SERVICE
    severity = FindingSeverity.LOW
    base_confidence = FindingConfidence.HIGH
    impact = "File shares, and any authentication weaknesses in SMB itself, are reachable from the network this scan was run from."
    remediation = "Restrict SMB (ports 139/445) to trusted internal segments only; never expose it directly to an untrusted network."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-200"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [s for s in _open(context) if s.port in (139, 445)]
        if not matches:
            return []
        ports = ", ".join(f"{s.port}/{s.protocol.value}" for s in matches)
        return [
            FindingCandidate(
                detail=f"SMB service open on: {ports}.",
                evidence_title="Open SMB port(s)",
                matched_services=matches,
            )
        ]


class RdpServiceExposedRule(CorrelationRule):
    rule_id = "SVC-004"
    title = "Remote Desktop (RDP) Service Exposed"
    description = "An open RDP service was detected on the standard RDP port."
    category = RuleCategory.SERVICE
    severity = FindingSeverity.MEDIUM
    base_confidence = FindingConfidence.HIGH
    impact = "RDP is a frequent target for credential-stuffing and brute-force attacks when reachable from an untrusted network."
    remediation = "Restrict RDP access to a VPN or bastion host; require network-level authentication and strong account lockout policies."
    references = (RuleReference(FindingReferenceType.CWE, "CWE-200"),)

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [s for s in _open(context) if s.port == 3389]
        if not matches:
            return []
        service = matches[0]
        return [
            FindingCandidate(
                detail=f"RDP service open on port {service.port}/{service.protocol.value}.",
                evidence_title=f"Open port {service.port}/{service.protocol.value}",
                matched_services=matches,
            )
        ]


_DATA_STORE_PORTS: dict[int, str] = {
    3306: "MySQL", 5432: "PostgreSQL", 1433: "Microsoft SQL Server", 27017: "MongoDB",
    6379: "Redis", 11211: "Memcached", 9200: "Elasticsearch", 9042: "Cassandra",
}
_DATA_STORE_PRODUCT_KEYWORDS = ("mysql", "postgres", "mongodb", "redis", "memcached", "elasticsearch", "cassandra", "mssql")


class DataStoreServiceExposedRule(CorrelationRule):
    rule_id = "SVC-005"
    title = "Database or Search Service Exposed to the Network"
    description = (
        "A service matching a known database, cache, or search-engine product/port was detected "
        "as reachable from the network this scan was run from. Many of these products ship with "
        "no authentication enabled by default."
    )
    category = RuleCategory.SERVICE
    severity = FindingSeverity.MEDIUM
    base_confidence = FindingConfidence.MEDIUM
    impact = "If authentication is not enforced, this service may allow unauthenticated read/write access to stored data from the network."
    remediation = "Bind data-store services to localhost or an internal-only interface, place them behind a firewall, and confirm authentication is enabled and enforced."
    references = (
        RuleReference(FindingReferenceType.CWE, "CWE-306"),
        RuleReference(FindingReferenceType.OWASP, "A01:2021"),
    )

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        matches = [
            s
            for s in _open(context)
            if s.port in _DATA_STORE_PORTS
            or any(keyword in (s.product or "").lower() for keyword in _DATA_STORE_PRODUCT_KEYWORDS)
        ]
        if not matches:
            return []
        candidates = []
        for service in matches:
            label = _DATA_STORE_PORTS.get(service.port, service.product or service.service_name or "data store")
            candidates.append(
                FindingCandidate(
                    detail=f"{label} reachable on port {service.port}/{service.protocol.value}"
                    + (f" (product: {service.product})" if service.product else "") + ".",
                    evidence_title=f"Open port {service.port}/{service.protocol.value} ({label})",
                    matched_services=[service],
                )
            )
        return candidates


RULES: tuple[type[CorrelationRule], ...] = (
    TelnetServiceExposedRule,
    FtpServiceExposedRule,
    SmbServiceExposedRule,
    RdpServiceExposedRule,
    DataStoreServiceExposedRule,
)
