"""SQLAlchemy ORM models.

Every model module is imported here so that :data:`backend.database.base.Base.metadata`
is fully populated as soon as this package is imported — required both by
Alembic autogenerate and by ``Base.metadata.create_all`` in tests.
"""

from backend.models.analyst_note import AnalystNote
from backend.models.application_setting import ApplicationSetting
from backend.models.assessment import Assessment
from backend.models.assessment_history import AssessmentHistoryEntry
from backend.models.assessment_tag import AssessmentTag
from backend.models.assessment_tool import AssessmentTool
from backend.models.attachment import Attachment
from backend.models.correlation_run import CorrelationRun
from backend.models.discovered_host import DiscoveredHost
from backend.models.execution_host import ExecutionHost
from backend.models.execution_observation import ExecutionObservation
from backend.models.finding import Finding, FindingEvidence, FindingObservation, FindingReference
from backend.models.fingerprint import Fingerprint
from backend.models.network_interface import NetworkInterface
from backend.models.observation import Observation
from backend.models.observation_evidence import ObservationEvidence
from backend.models.operating_system import OperatingSystem
from backend.models.raw_tool_output import RawToolOutput
from backend.models.report import Report
from backend.models.service import Service
from backend.models.target import Target
from backend.models.technology import Technology
from backend.models.tool import Tool, ToolConfiguration
from backend.models.tool_execution import ToolExecution

__all__ = [
    "AnalystNote",
    "ApplicationSetting",
    "Assessment",
    "AssessmentHistoryEntry",
    "AssessmentTag",
    "AssessmentTool",
    "Attachment",
    "CorrelationRun",
    "DiscoveredHost",
    "ExecutionHost",
    "ExecutionObservation",
    "Finding",
    "FindingEvidence",
    "FindingObservation",
    "FindingReference",
    "Fingerprint",
    "NetworkInterface",
    "Observation",
    "ObservationEvidence",
    "OperatingSystem",
    "RawToolOutput",
    "Report",
    "Service",
    "Target",
    "Technology",
    "Tool",
    "ToolConfiguration",
    "ToolExecution",
]
