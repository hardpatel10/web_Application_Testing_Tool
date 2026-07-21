"""The Correlation Engine's write side: turns real inventory rows into ``Finding`` rows.

The *only* place a :class:`~backend.correlation.models.FindingCandidate`
becomes a persisted ``Finding``/``FindingEvidence``/``FindingReference``/
``FindingObservation`` row set -- mirrors
:class:`~backend.services.host_inventory_service.HostInventoryService`'s
role for Phase 8's inventory tables. Deliberately never imports
``backend.workers`` (the frozen execution engine) or the Nmap plugin: this
runs entirely against whatever ``DiscoveredHost``/``Service``/``Technology``/
``OperatingSystem``/``Observation`` rows are already durably persisted, on
its own explicit trigger (``POST /correlation/run``), never as a side effect
of a job completing.

Algorithm, per host, inside one DB transaction: load every ``Service``/
``Technology``/``OperatingSystem``/``Observation`` currently on the host
into one :class:`~backend.correlation.models.RuleContext`, evaluate every
registered rule against it, and for each rule that returned one or more
:class:`~backend.correlation.models.FindingCandidate`\\ s, find-or-create
**one** ``Finding`` keyed on ``(assessment_id, fingerprint)`` where
``fingerprint`` is derived from ``(rule_id, host.fingerprint)`` -- so a rule
fires at most once per host, and every candidate it returned this run
becomes one more piece of evidence merged onto that same finding (the
"Merging" requirement: "If multiple observations indicate the same issue,
create ONE finding, maintain all evidence").
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import NotFoundError
from backend.correlation.base import CorrelationRule
from backend.correlation.models import FindingCandidate, RuleContext
from backend.correlation.registry import CorrelationRuleRegistry, get_rule_registry
from backend.models.assessment import Assessment
from backend.models.base import utcnow
from backend.models.correlation_run import CorrelationRun
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import CorrelationRunStatus, FindingConfidence, FindingStatus
from backend.models.execution_host import ExecutionHost
from backend.models.execution_observation import ExecutionObservation
from backend.models.finding import Finding, FindingEvidence, FindingObservation, FindingReference
from backend.models.observation import Observation
from backend.models.operating_system import OperatingSystem
from backend.models.service import Service
from backend.models.technology import Technology
from backend.models.tool import Tool
from backend.models.tool_execution import ToolExecution
from backend.services import fingerprinting
from backend.services.query_scoping import owned_by_active_assessment

_CONFIDENCE_ORDER = [FindingConfidence.LOW, FindingConfidence.MEDIUM, FindingConfidence.HIGH, FindingConfidence.CONFIRMED]


def _bump_confidence(base: FindingConfidence, levels: int) -> FindingConfidence:
    """Move ``base`` up the LOW -> MEDIUM -> HIGH -> CONFIRMED ladder by ``levels``, capped at CONFIRMED."""
    index = _CONFIDENCE_ORDER.index(base)
    return _CONFIDENCE_ORDER[min(index + levels, len(_CONFIDENCE_ORDER) - 1)]


@dataclass
class CorrelationSummary:
    """Counts of what one :class:`CorrelationService` run actually did -- for logging and ``CorrelationRun``."""

    hosts_evaluated: int = 0
    rules_evaluated: int = 0
    findings_created: int = 0
    findings_updated: int = 0
    findings_unchanged: int = 0
    rule_ids: set[str] = field(default_factory=set)


class CorrelationService:
    """Evaluates every registered rule against every host's current, real inventory state."""

    def __init__(self, session: AsyncSession, registry: CorrelationRuleRegistry | None = None) -> None:
        self._session = session
        self._registry = registry or get_rule_registry()

    async def correlate_assessment(self, assessment_id: uuid.UUID) -> CorrelationSummary:
        """Run every rule against every host in one assessment."""
        assessment = await self._session.get(Assessment, assessment_id)
        if assessment is None or assessment.deleted_at is not None:
            raise NotFoundError(f"Assessment {assessment_id} not found.")

        run = CorrelationRun(assessment_id=assessment_id, status=CorrelationRunStatus.RUNNING, started_at=utcnow())
        self._session.add(run)
        await self._session.flush()
        try:
            host_ids = (
                await self._session.execute(select(DiscoveredHost.id).where(DiscoveredHost.assessment_id == assessment_id))
            ).scalars().all()
            summary = await self._correlate_hosts(assessment_id, list(host_ids))
        except Exception as exc:
            run.status = CorrelationRunStatus.FAILED
            run.completed_at = utcnow()
            run.error_message = str(exc)[:2000]
            raise
        self._finalize_run(run, summary)
        return summary

    async def correlate_all(self) -> CorrelationSummary:
        """Run every rule against every host across every assessment."""
        run = CorrelationRun(assessment_id=None, status=CorrelationRunStatus.RUNNING, started_at=utcnow())
        self._session.add(run)
        await self._session.flush()
        overall = CorrelationSummary()
        try:
            assessment_host_pairs = (
                await self._session.execute(
                    select(DiscoveredHost.assessment_id, DiscoveredHost.id).where(
                        owned_by_active_assessment(DiscoveredHost.assessment_id)
                    )
                )
            ).all()
            by_assessment: dict[uuid.UUID, list[uuid.UUID]] = {}
            for assessment_id, host_id in assessment_host_pairs:
                by_assessment.setdefault(assessment_id, []).append(host_id)
            for assessment_id, host_ids in by_assessment.items():
                partial = await self._correlate_hosts(assessment_id, host_ids)
                overall.hosts_evaluated += partial.hosts_evaluated
                overall.rules_evaluated += partial.rules_evaluated
                overall.findings_created += partial.findings_created
                overall.findings_updated += partial.findings_updated
                overall.findings_unchanged += partial.findings_unchanged
                overall.rule_ids |= partial.rule_ids
        except Exception as exc:
            run.status = CorrelationRunStatus.FAILED
            run.completed_at = utcnow()
            run.error_message = str(exc)[:2000]
            raise
        self._finalize_run(run, overall)
        return overall

    def _finalize_run(self, run: CorrelationRun, summary: CorrelationSummary) -> None:
        run.status = CorrelationRunStatus.COMPLETED
        run.completed_at = utcnow()
        run.hosts_evaluated = summary.hosts_evaluated
        run.rules_evaluated = summary.rules_evaluated
        run.findings_created = summary.findings_created
        run.findings_updated = summary.findings_updated

    # -- Per-assessment evaluation --------------------------------------------

    async def _correlate_hosts(self, assessment_id: uuid.UUID, host_ids: list[uuid.UUID]) -> CorrelationSummary:
        summary = CorrelationSummary()
        rules = self._registry.all_rules()
        now = utcnow()
        for host_id in host_ids:
            host = await self._session.get(DiscoveredHost, host_id)
            if host is None:
                continue
            context = await self._build_context(host)
            plugin_name = await self._resolve_host_plugin(host)
            summary.hosts_evaluated += 1
            for rule in rules:
                summary.rules_evaluated += 1
                summary.rule_ids.add(rule.rule_id)
                candidates = rule.evaluate(context)
                if not candidates:
                    continue
                created = await self._upsert_finding(
                    assessment_id=assessment_id, host=host, plugin_name=plugin_name,
                    rule=rule, candidates=candidates, now=now,
                )
                if created is True:
                    summary.findings_created += 1
                elif created is False:
                    summary.findings_updated += 1
        return summary

    async def _build_context(self, host: DiscoveredHost) -> RuleContext:
        services = list(
            (await self._session.execute(select(Service).where(Service.host_id == host.id))).scalars().all()
        )
        technologies = list(
            (await self._session.execute(select(Technology).where(Technology.host_id == host.id))).scalars().all()
        )
        operating_systems = list(
            (
                await self._session.execute(select(OperatingSystem).where(OperatingSystem.host_id == host.id))
            ).scalars().all()
        )
        observations = list(
            (await self._session.execute(select(Observation).where(Observation.host_id == host.id))).scalars().all()
        )
        return RuleContext(
            host=host, services=services, technologies=technologies,
            operating_systems=operating_systems, observations=observations,
        )

    async def _resolve_host_plugin(self, host: DiscoveredHost) -> str | None:
        """The tool that most recently discovered this host, e.g. 'nmap' -- real, joined, never guessed."""
        if host.source_execution_id is None:
            return None
        row = (
            await self._session.execute(
                select(Tool.name)
                .join(ToolExecution, ToolExecution.tool_id == Tool.id)
                .where(ToolExecution.id == host.source_execution_id)
            )
        ).scalar_one_or_none()
        return row

    # -- One rule's candidates -> one Finding -----------------------------------

    async def _upsert_finding(
        self,
        *,
        assessment_id: uuid.UUID,
        host: DiscoveredHost,
        plugin_name: str | None,
        rule: CorrelationRule,
        candidates: list[FindingCandidate],
        now: datetime,
    ) -> bool:
        """Find-or-create the one Finding for ``(rule, host)`` and merge every candidate's evidence onto it.

        Returns ``True`` if a new Finding row was created, ``False`` if an
        existing one was updated/re-confirmed.
        """
        fp = fingerprinting.finding_fingerprint(rule_id=rule.rule_id, host_fingerprint_value=host.fingerprint)
        existing = (
            await self._session.execute(
                select(Finding).where(
                    Finding.assessment_id == assessment_id, Finding.host_id == host.id, Finding.fingerprint == fp
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            finding = Finding(
                assessment_id=assessment_id,
                host_id=host.id,
                source_execution_id=host.source_execution_id,
                rule_id=rule.rule_id,
                plugin=plugin_name,
                title=rule.title,
                description=rule.description,
                impact=rule.impact,
                severity=rule.severity,
                confidence=rule.base_confidence,
                category=rule.category.value,
                remediation=rule.remediation,
                status=FindingStatus.OPEN,
                fingerprint=fp,
                first_seen=now,
                last_seen=now,
            )
            self._session.add(finding)
            await self._session.flush()
            created = True
        else:
            finding = existing
            finding.last_seen = now
            finding.source_execution_id = host.source_execution_id or finding.source_execution_id
            created = False

        await self._merge_references(finding, rule)
        matched_observation_ids = await self._merge_evidence_and_observations(finding, plugin_name, candidates)
        finding.confidence = await self._compute_confidence(rule, host, matched_observation_ids)

        return created

    async def _merge_references(self, finding: Finding, rule: CorrelationRule) -> None:
        existing = {
            (r.reference_type, r.reference_value)
            for r in (
                await self._session.execute(select(FindingReference).where(FindingReference.finding_id == finding.id))
            ).scalars().all()
        }
        for ref in rule.references:
            if (ref.reference_type, ref.value) not in existing:
                self._session.add(
                    FindingReference(finding_id=finding.id, reference_type=ref.reference_type, reference_value=ref.value)
                )
                existing.add((ref.reference_type, ref.value))

    async def _merge_evidence_and_observations(
        self, finding: Finding, plugin_name: str | None, candidates: list[FindingCandidate]
    ) -> set[uuid.UUID]:
        existing_evidence = {
            (e.title, e.content)
            for e in (
                await self._session.execute(select(FindingEvidence).where(FindingEvidence.finding_id == finding.id))
            ).scalars().all()
        }
        existing_links = {
            link.observation_id
            for link in (
                await self._session.execute(select(FindingObservation).where(FindingObservation.finding_id == finding.id))
            ).scalars().all()
        }

        source_tool = plugin_name or "correlation-engine"
        for candidate in candidates:
            key = (candidate.evidence_title, candidate.detail)
            if key not in existing_evidence:
                self._session.add(
                    FindingEvidence(
                        finding_id=finding.id, source_tool=source_tool,
                        title=candidate.evidence_title, content=candidate.detail,
                    )
                )
                existing_evidence.add(key)
            for observation in candidate.matched_observations:
                if observation.id not in existing_links:
                    self._session.add(FindingObservation(finding_id=finding.id, observation_id=observation.id))
                    existing_links.add(observation.id)

        await self._session.flush()
        return existing_links

    async def _compute_confidence(
        self, rule: CorrelationRule, host: DiscoveredHost, matched_observation_ids: set[uuid.UUID]
    ) -> FindingConfidence:
        """Base confidence, bumped once per corroborating signal: >=2 supporting observations, >=2 confirming scans."""
        bumps = 0
        if len(matched_observation_ids) >= 2:
            bumps += 1

        if matched_observation_ids:
            execution_count = (
                await self._session.execute(
                    select(func.count(func.distinct(ExecutionObservation.execution_id))).where(
                        ExecutionObservation.observation_id.in_(matched_observation_ids)
                    )
                )
            ).scalar_one()
        else:
            execution_count = (
                await self._session.execute(
                    select(func.count(func.distinct(ExecutionHost.execution_id))).where(
                        ExecutionHost.host_id == host.id
                    )
                )
            ).scalar_one()
        if execution_count and execution_count >= 2:
            bumps += 1

        return _bump_confidence(rule.base_confidence, bumps)
