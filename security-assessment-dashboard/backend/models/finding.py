"""The ``Finding``, ``FindingEvidence``, ``FindingReference``, and ``FindingObservation`` models.

A ``Finding`` is the Correlation Engine's output: a conclusion a deterministic
:class:`~backend.correlation.base.CorrelationRule` drew from one or more
``Observation``/``Service``/``Technology``/``OperatingSystem`` rows for one
``DiscoveredHost`` — never fabricated, never scored by an LLM, never
containing an invented CVE (see ``backend.correlation.rules``). Scoped
directly to ``assessment_id``/``host_id`` (denormalized, like
``Observation.plugin``) so dashboard aggregation never has to join through
``ToolExecution`` to answer "how many findings does this assessment have."

Deduplicated exactly like ``DiscoveredHost``/``Service``/``Observation``:
re-running the Correlation Engine against the same host re-evaluates every
rule and finds the same ``(assessment_id, host_id, fingerprint)`` row rather
than inserting a duplicate — ``fingerprint`` is ``rule_id`` + the host's own
fingerprint (see ``backend.services.fingerprinting.finding_fingerprint``), so
a rule produces at most one durable ``Finding`` per host, with ``first_seen``/
``last_seen`` tracking how long the condition has persisted across scans.
``host_id`` is part of the merge key, not just ``fingerprint``, because a
host's fingerprint (MAC/IP/hostname) is not itself scoped to the
``Target`` that discovered it — two different targets in the same
assessment can legitimately discover the same physical host, and each
must keep its own independent findings (see the unique index below).

``source_execution_id`` is nullable + ``SET NULL`` (Phase 8's
``Observation.execution_id`` pattern): a ``Finding`` belongs to the
``Assessment``/``DiscoveredHost`` now, not to any one execution, so deleting
an old job's history must never delete a still-valid finding.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from backend.models.enums import FindingConfidence, FindingReferenceType, FindingSeverity, FindingStatus

if TYPE_CHECKING:
    from backend.models.assessment import Assessment
    from backend.models.discovered_host import DiscoveredHost
    from backend.models.observation import Observation
    from backend.models.tool_execution import ToolExecution


class Finding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One correlated conclusion, durable and deduplicated across repeated Correlation Engine runs."""

    __tablename__ = "findings"
    __table_args__ = (
        # Scoped by host_id, not just assessment_id + fingerprint: `fingerprint`
        # is derived from host *identity* (MAC/IP/hostname, see
        # backend.services.fingerprinting.host_fingerprint), which is not itself
        # target-scoped -- the same IP can legitimately back two different
        # DiscoveredHost rows in one assessment (added as its own target, and
        # again inside a swept CIDR target; see DiscoveredHost's docstring).
        # Without host_id here, a rule finding for the second host would match
        # this index on (assessment_id, fingerprint) alone and silently merge
        # onto the first host's Finding -- collapsing two different Assessment
        # Targets' evidence onto one row.
        Index("uq_findings_assessment_id_host_id_fingerprint", "assessment_id", "host_id", "fingerprint", unique=True),
        Index("ix_findings_assessment_id_severity", "assessment_id", "severity"),
        Index("ix_findings_host_id_severity", "host_id", "severity"),
        CheckConstraint(
            "cvss_score IS NULL OR (cvss_score >= 0 AND cvss_score <= 10)",
            name="cvss_score_range",
        ),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discovered_hosts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Null only for a (currently unused) assessment-wide rule with no single owning host.",
    )
    #: Denormalized "most recently re-confirmed by" pointer, exactly like Observation.execution_id.
    source_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, doc="The CorrelationRule.rule_id that produced this finding."
    )
    plugin: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True, doc="Originating tool of the rule's primary evidence, e.g. 'nmap'."
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        index=True,
    )
    confidence: Mapped[FindingConfidence] = mapped_column(
        Enum(FindingConfidence, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        default=FindingConfidence.MEDIUM,
    )
    category: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True, doc="The rule's RuleCategory value, e.g. 'ssh'/'tls'/'service'."
    )
    cvss_score: Mapped[float | None] = mapped_column(nullable=True)
    cwe: Mapped[str | None] = mapped_column(String(20), nullable=True)
    owasp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=False,
        default=FindingStatus.OPEN,
        index=True,
    )
    #: Deterministic merge key from backend.services.fingerprinting.finding_fingerprint.
    fingerprint: Mapped[str] = mapped_column(String(80), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    assessment: Mapped["Assessment"] = relationship(back_populates="findings")
    host: Mapped["DiscoveredHost | None"] = relationship(back_populates="findings")
    source_execution: Mapped["ToolExecution | None"] = relationship()
    evidence: Mapped[list["FindingEvidence"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan", passive_deletes=True
    )
    references: Mapped[list["FindingReference"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan", passive_deletes=True
    )
    observation_links: Mapped[list["FindingObservation"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan", passive_deletes=True
    )


class FindingEvidence(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Supporting evidence for a finding, captured verbatim from its source.

    Append-only: new evidence is added as it is gathered, existing rows are
    never overwritten.
    """

    __tablename__ = "finding_evidence"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_tool: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    finding: Mapped["Finding"] = relationship(back_populates="evidence")


class FindingReference(UUIDPrimaryKeyMixin, Base):
    """An external reference (CWE, OWASP, CAPEC, CVE, vendor advisory, docs) attached to a finding.

    Always sourced from a rule's own static ``references`` tuple — the
    Correlation Engine never invents an id here (see ``.claude/CLAUDE.md``
    and this phase's explicit "References must be real" instruction).
    """

    __tablename__ = "finding_references"
    __table_args__ = (
        Index(
            "uq_finding_references_finding_id_type_value",
            "finding_id",
            "reference_type",
            "reference_value",
            unique=True,
        ),
    )

    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference_type: Mapped[FindingReferenceType] = mapped_column(
        Enum(FindingReferenceType, native_enum=False, validate_strings=True, create_constraint=True, length=32),
        nullable=False,
    )
    reference_value: Mapped[str] = mapped_column(String(255), nullable=False)

    finding: Mapped["Finding"] = relationship(back_populates="references")


class FindingObservation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One record of one observation supporting one finding.

    Mirrors ``ExecutionObservation``'s join-table shape: this is the durable
    "all observation references" the Correlation Engine's brief requires —
    every observation a rule matched to produce (or re-confirm) a finding,
    kept even as new observations are added on a later run.
    """

    __tablename__ = "finding_observations"
    __table_args__ = (
        Index("uq_finding_observations_finding_id_observation_id", "finding_id", "observation_id", unique=True),
    )

    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("observations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    finding: Mapped["Finding"] = relationship(back_populates="observation_links")
    observation: Mapped["Observation"] = relationship()
