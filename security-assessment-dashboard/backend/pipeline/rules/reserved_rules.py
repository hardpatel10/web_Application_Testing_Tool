"""Reserved Rules: services this platform explicitly declines to run a scanner against yet.

Per the Assessment Pipeline brief: SSH/SMB/database services get a plain,
neutral observation recorded (not a scan) -- dedicated scanners for each are
reserved for a future phase, exactly like this project already reserves
SSLScan execution (still detection-only) and every not-yet-built plugin.
"""

from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import ObservationCategory, PortState
from backend.models.service import Service
from backend.pipeline.base import PipelineRule
from backend.pipeline.models import PipelineDecision, SkipDecision

_SSH_PORTS = {22}
_SMB_PORTS = {139, 445}
_DATABASE_PORTS: dict[int, str] = {
    3306: "MySQL", 5432: "PostgreSQL", 1433: "Microsoft SQL Server", 1521: "Oracle", 27017: "MongoDB",
}


class SshReservedRule(PipelineRule):
    rule_id = "PIPE-SSH-001"
    description = "SSH service -- no web scanner applies; a dedicated SSH scanner is reserved for a future phase."

    def evaluate(self, service: Service, host: DiscoveredHost) -> PipelineDecision:
        if service.state != PortState.OPEN:
            return None
        if service.port not in _SSH_PORTS and (service.service_name or "").lower() != "ssh":
            return None
        return SkipDecision(
            reason="SSH service detected. Dedicated SSH scanner reserved for a future phase.",
            rule_id=self.rule_id,
            category=ObservationCategory.AUTH,
            reserved_tool_names=("nikto", "nuclei"),
        )


class SmbReservedRule(PipelineRule):
    rule_id = "PIPE-SMB-001"
    description = "SMB/CIFS service -- no web scanner applies; a dedicated SMB scanner is reserved for a future phase."

    def evaluate(self, service: Service, host: DiscoveredHost) -> PipelineDecision:
        if service.state != PortState.OPEN:
            return None
        name = (service.service_name or "").lower()
        if service.port not in _SMB_PORTS and name not in ("netbios-ssn", "microsoft-ds"):
            return None
        return SkipDecision(
            reason="SMB service detected. Dedicated SMB scanner reserved for a future phase.",
            rule_id=self.rule_id,
            category=ObservationCategory.NETWORK,
            reserved_tool_names=("nikto", "nuclei"),
        )


class DatabaseReservedRule(PipelineRule):
    rule_id = "PIPE-DB-001"
    description = "Database service -- no web scanner applies; dedicated database plugins are reserved for a future phase."

    def evaluate(self, service: Service, host: DiscoveredHost) -> PipelineDecision:
        if service.state != PortState.OPEN:
            return None
        label = _DATABASE_PORTS.get(service.port)
        if label is None:
            return None
        return SkipDecision(
            reason=f"{label} database service detected. Dedicated database plugins reserved for a future phase.",
            rule_id=self.rule_id,
            category=ObservationCategory.CONFIGURATION,
            reserved_tool_names=("nikto", "nuclei"),
        )


RULES: tuple[type[PipelineRule], ...] = (
    SshReservedRule,
    SmbReservedRule,
    DatabaseReservedRule,
)
