"""Enumerations shared by the ORM models.

Each enum is stored as a plain ``VARCHAR`` with a ``CHECK`` constraint
(``native_enum=False`` at the column definition site) rather than a native
database ``ENUM`` type, so the same schema works unmodified on both SQLite
and PostgreSQL.
"""

from enum import StrEnum


class AssessmentType(StrEnum):
    """Category of security assessment being performed."""

    NETWORK = "network"
    WEB_APPLICATION = "web_application"
    API = "api"
    MOBILE = "mobile"
    CLOUD = "cloud"
    INTERNAL = "internal"
    EXTERNAL = "external"
    CUSTOM = "custom"


class AssessmentStatus(StrEnum):
    """Lifecycle state of an assessment.

    ``ARCHIVED`` is a workflow state (hides the assessment from the default
    list view but keeps it fully intact and restorable); it is distinct
    from a soft delete, which uses ``Assessment.deleted_at`` instead so
    that "deleted" and "archived" remain orthogonal, independently
    reversible concepts.
    """

    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class TargetType(StrEnum):
    """Kind of value stored in ``Target.target_value``."""

    IPV4 = "ipv4"
    IPV6 = "ipv6"
    CIDR = "cidr"
    HOSTNAME = "hostname"
    DOMAIN = "domain"
    URL = "url"


class AssessmentHistoryEventType(StrEnum):
    """Kind of lifecycle event recorded in an assessment's history log."""

    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    ARCHIVED = "archived"
    RESTORED = "restored"
    DELETED = "deleted"
    DUPLICATED = "duplicated"
    TARGET_ADDED = "target_added"
    TARGET_UPDATED = "target_updated"
    TARGET_REMOVED = "target_removed"
    TARGETS_IMPORTED = "targets_imported"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_FINISHED = "execution_finished"
    EXECUTION_CANCELLED = "execution_cancelled"
    JOB_FAILED = "job_failed"


class ToolStatus(StrEnum):
    """Discovery-derived lifecycle status of one cataloged tool.

    Distinct from ``ToolHealthStatus``: this describes *whether the tool
    can be used at all* (found on disk, disabled by the user, etc.);
    health describes *how well it's working* once installed.
    """

    INSTALLED = "installed"
    MISSING = "missing"
    DISABLED = "disabled"
    MISCONFIGURED = "misconfigured"
    UNSUPPORTED_VERSION = "unsupported_version"


class ToolHealthStatus(StrEnum):
    """Coarse health-check result surfaced by Tool Management.

    Deliberately a different (coarser, 3-value) vocabulary than
    :class:`backend.plugins.models.enums.PluginHealthStatus` (the plugin
    framework's own 5-value ``health()`` result) — this is the DB/API-facing
    simplification Phase 5 asks for; ``ToolService`` maps one to the other.
    """

    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"


class ToolExecutionStatus(StrEnum):
    """Lifecycle state of one tool execution (one job in the execution engine).

    Ordered roughly by lifecycle progression. ``QUEUED`` is planned-and-
    waiting-for-a-worker-slot; ``PREPARING`` is dequeued and setting up
    (creating output directories, resolving the command) but not yet
    spawned. ``SKIPPED`` is a planner-time decision (e.g. the tool cannot
    validate this target, or the tool is not installed/enabled) — it is
    never queued or run.
    """

    PENDING = "pending"
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class RawOutputFormat(StrEnum):
    """Serialization format of a captured raw tool output."""

    XML = "xml"
    JSON = "json"
    TXT = "txt"
    HTML = "html"
    CSV = "csv"


class FindingSeverity(StrEnum):
    """Severity rating of a normalized finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingConfidence(StrEnum):
    """Analyst/tool confidence that a finding is a true positive."""

    CONFIRMED = "confirmed"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingStatus(StrEnum):
    """Triage state of a finding."""

    OPEN = "open"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"
    REMEDIATED = "remediated"
    DUPLICATE = "duplicate"


class FindingReferenceType(StrEnum):
    """Kind of external reference attached to a finding."""

    CWE = "cwe"
    OWASP = "owasp"
    CAPEC = "capec"
    CVE = "cve"
    VENDOR_URL = "vendor_url"
    DOCUMENTATION_URL = "documentation_url"


class ReportType(StrEnum):
    """Output format of a generated report."""

    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


class HostState(StrEnum):
    """Reachability of one host discovered by a scan, as the scanner reported it."""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class NetworkProtocol(StrEnum):
    """Transport protocol of one discovered service."""

    TCP = "tcp"
    UDP = "udp"


class PortState(StrEnum):
    """Nmap's own port-state vocabulary, stored verbatim rather than collapsed."""

    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    OPEN_FILTERED = "open|filtered"
    CLOSED_FILTERED = "closed|filtered"
    UNFILTERED = "unfiltered"


class HostType(StrEnum):
    """Kind of asset a discovered host represents."""

    HOST = "host"
    WEBSITE = "website"
    API = "api"
    DOMAIN = "domain"
    IP = "ip"


class TechnologyCategory(StrEnum):
    """Coarse grouping of a detected software/product signature."""

    WEB_SERVER = "web_server"
    DATABASE = "database"
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    MIDDLEWARE = "middleware"
    OPERATING_SYSTEM = "operating_system"
    OTHER = "other"


class ObservationCategory(StrEnum):
    """Coarse grouping of an observation, independent of its free-text ``observation_type``."""

    NETWORK = "network"
    WEB = "web"
    TLS = "tls"
    AUTH = "auth"
    CONFIGURATION = "configuration"
    OS = "os"
    OTHER = "other"


class FingerprintType(StrEnum):
    """Kind of protocol-level identity evidence captured in a ``Fingerprint`` row."""

    SSH = "ssh"
    TLS = "tls"
    HTTP = "http"
    SMB = "smb"
    BANNER = "banner"
    HASH = "hash"


class RuleCategory(StrEnum):
    """Grouping of a correlation rule (and the ``Finding`` it produces), per the rule engine's own taxonomy."""

    SERVICE = "service"
    TECHNOLOGY = "technology"
    OPERATING_SYSTEM = "operating_system"
    PROTOCOL = "protocol"
    CONFIGURATION = "configuration"
    TLS = "tls"
    SSH = "ssh"
    SMB = "smb"
    HTTP = "http"
    GENERAL = "general"


class CorrelationRunStatus(StrEnum):
    """Lifecycle state of one ``CorrelationRun`` (one execution of the rule engine)."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
