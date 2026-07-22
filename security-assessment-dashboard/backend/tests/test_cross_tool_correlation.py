"""Tests for the cross-tool Correlation rules (Phase 11).

Mirrors ``test_correlation.py``'s own conventions: pure rule-level unit
tests need no DB; the full end-to-end test seeds an assessment/host/
technology/observations directly via a real DB session (exactly the shape
``HostInventoryService`` would have produced from real Nmap/Nikto/Nuclei
executions) and drives the real ``CorrelationService`` against a real
SQLite database -- no mocking, per ``.claude/CLAUDE.md``.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.correlation.models import RuleContext
from backend.correlation.rules.cross_tool_rules import (
    KnownVulnerableTechnologyConfirmedByTemplateRule,
    MultiToolConfirmedCveRule,
)
from backend.correlation.rules.tls_rules import SelfSignedCertificateRule
from backend.database.session import background_session
from backend.models.assessment import Assessment
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import (
    AssessmentType,
    HostState,
    HostType,
    ObservationCategory,
    TargetType,
    TechnologyCategory,
    ToolExecutionStatus,
)
from backend.models.execution_host import ExecutionHost
from backend.models.finding import Finding, FindingObservation
from backend.models.observation import Observation
from backend.models.target import Target
from backend.models.technology import Technology
from backend.models.tool import Tool
from backend.models.tool_execution import ToolExecution
from backend.services import fingerprinting
from backend.services.correlation_service import CorrelationService

# -- Pure rule unit tests: no DB ----------------------------------------------


def _make_host(**overrides) -> DiscoveredHost:
    defaults = dict(
        id=uuid.uuid4(), target_id=uuid.uuid4(), assessment_id=uuid.uuid4(), hostname="host", ipv4="10.0.0.1",
        host_type=HostType.HOST, state=HostState.UP, fingerprint="ipv4:test",
        first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return DiscoveredHost(**defaults)


def _make_observation(host: DiscoveredHost, *, plugin: str, detail: str, source: str = "test") -> Observation:
    return Observation(
        id=uuid.uuid4(), host_id=host.id, plugin=plugin, source=source, category=ObservationCategory.WEB,
        title=source, detail=detail, fingerprint=f"observation:{uuid.uuid4()}",
        first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
    )


def _make_technology(host: DiscoveredHost, *, name: str, version: str) -> Technology:
    return Technology(
        id=uuid.uuid4(), host_id=host.id, name=name, version=version, category=TechnologyCategory.OTHER,
        first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
    )


def _empty_context(host: DiscoveredHost) -> RuleContext:
    return RuleContext(host=host, services=[], technologies=[], operating_systems=[], observations=[])


def test_multi_tool_cve_rule_fires_when_same_cve_seen_from_two_plugins() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.observations = [
        _make_observation(host, plugin="nikto", detail="Apache outdated, CVE-2021-41773 path traversal"),
        _make_observation(host, plugin="nuclei", detail="Severity: critical\nCVE: CVE-2021-41773\nCVSS: 9.8"),
    ]
    candidates = MultiToolConfirmedCveRule().evaluate(context)
    assert len(candidates) == 1
    assert "CVE-2021-41773" in candidates[0].detail
    assert len(candidates[0].matched_observations) == 2


def test_multi_tool_cve_rule_does_not_fire_from_a_single_plugin() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.observations = [
        _make_observation(host, plugin="nuclei", detail="CVE: CVE-2021-41773"),
        _make_observation(host, plugin="nuclei", detail="CVE: CVE-2021-41773 (second template)"),
    ]
    assert MultiToolConfirmedCveRule().evaluate(context) == []


def test_multi_tool_cve_rule_does_not_fire_without_any_cve() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.observations = [
        _make_observation(host, plugin="nmap", detail="Apache/2.4.49 server header"),
        _make_observation(host, plugin="nikto", detail="Server leaks inode via ETags"),
    ]
    assert MultiToolConfirmedCveRule().evaluate(context) == []


def test_known_vulnerable_technology_rule_requires_live_nuclei_confirmation() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.technologies = [_make_technology(host, name="Apache httpd", version="2.4.49")]
    # No nuclei observation confirming the CVE yet -- must not fire from the version match alone.
    assert KnownVulnerableTechnologyConfirmedByTemplateRule().evaluate(context) == []


def test_self_signed_certificate_rule_merges_evidence_from_nmap_and_sslscan() -> None:
    """The SSLScan phase's own worked example: the same TLS fact (a self-signed certificate),
    reported once by Nmap's ssl-cert NSE script and once by the SSLScan plugin, must merge into
    one Finding backed by evidence from both tools -- not two separate, duplicated findings."""
    host = _make_host()
    context = _empty_context(host)
    context.observations = [
        _make_observation(host, plugin="nmap", source="ssl-cert", detail="Subject: commonName=host\nself signed"),
        _make_observation(host, plugin="sslscan", source="sslscan-cert", detail="Subject: host\nThis certificate is self-signed."),
    ]
    candidates = SelfSignedCertificateRule().evaluate(context)
    assert len(candidates) == 1
    assert len(candidates[0].matched_observations) == 2


def test_known_vulnerable_technology_rule_fires_with_nuclei_confirmation_and_nikto_support() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.technologies = [_make_technology(host, name="Apache httpd", version="2.4.49")]
    context.observations = [
        _make_observation(host, plugin="nikto", detail="Apache/2.4.49 appears outdated"),
        _make_observation(host, plugin="nuclei", detail="Severity: critical\nCVE: CVE-2021-41773\nCVSS: 9.8"),
    ]
    candidates = KnownVulnerableTechnologyConfirmedByTemplateRule().evaluate(context)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert "CVE-2021-41773" in candidate.detail
    assert len(candidate.matched_technologies) == 1
    # Both the confirming nuclei observation and the supporting nikto observation are linked.
    assert len(candidate.matched_observations) == 2
    assert {obs.plugin for obs in candidate.matched_observations} == {"nikto", "nuclei"}


def test_known_vulnerable_technology_rule_ignores_unrelated_version() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.technologies = [_make_technology(host, name="Apache httpd", version="2.4.41")]
    context.observations = [_make_observation(host, plugin="nuclei", detail="CVE: CVE-2021-41773")]
    assert KnownVulnerableTechnologyConfirmedByTemplateRule().evaluate(context) == []


# -- Full end-to-end: Nmap technology + Nikto observation + Nuclei observation -> ONE Finding ---


async def _seed_multi_tool_vulnerable_host(session) -> tuple[Assessment, DiscoveredHost]:
    assessment = Assessment(name=f"cross-tool-{uuid.uuid4()}", assessment_type=AssessmentType.WEB_APPLICATION)
    session.add(assessment)
    await session.flush()

    target = Target(assessment_id=assessment.id, target_type=TargetType.URL, target_value="https://example.com")
    session.add(target)

    nmap_tool = (await session.execute(select(Tool).where(Tool.name == "nmap"))).scalar_one_or_none()
    if nmap_tool is None:
        nmap_tool = Tool(name="nmap", display_name="Nmap")
        session.add(nmap_tool)
    await session.flush()

    nmap_execution = ToolExecution(
        assessment_id=assessment.id, target_id=target.id, tool_id=nmap_tool.id, status=ToolExecutionStatus.COMPLETED
    )
    session.add(nmap_execution)
    await session.flush()

    now = datetime.now(timezone.utc)
    host_fp = fingerprinting.host_fingerprint(mac_address=None, ipv4=None, ipv6=None, hostname="example.com")
    host = DiscoveredHost(
        target_id=target.id, assessment_id=assessment.id, hostname="example.com", host_type=HostType.WEBSITE,
        state=HostState.UP, fingerprint=host_fp, first_seen=now, last_seen=now, source_execution_id=nmap_execution.id,
    )
    session.add(host)
    await session.flush()
    session.add(ExecutionHost(execution_id=nmap_execution.id, host_id=host.id, is_new=True))

    # Nmap: fingerprinted the vulnerable Apache version.
    session.add(Technology(host_id=host.id, name="Apache httpd", version="2.4.49", category=TechnologyCategory.OTHER,
                            first_seen=now, last_seen=now, source_execution_id=nmap_execution.id))

    # Nikto: observed the same version in its own server-header check.
    session.add(Observation(
        host_id=host.id, plugin="nikto", source="nikto", category=ObservationCategory.WEB,
        title="Server header", detail="Apache/2.4.49 appears to be outdated",
        fingerprint=f"observation:{uuid.uuid4()}", first_seen=now, last_seen=now,
    ))

    # Nuclei: live template match confirming the specific CVE.
    session.add(Observation(
        host_id=host.id, plugin="nuclei", source="nuclei", category=ObservationCategory.WEB,
        title="Apache 2.4.49 - Path Traversal", detail="Severity: critical\nCVE: CVE-2021-41773\nCWE: CWE-22\nCVSS: 9.8",
        fingerprint=f"observation:{uuid.uuid4()}", first_seen=now, last_seen=now,
    ))

    await session.flush()
    return assessment, host


@pytest.mark.asyncio
async def test_nmap_nikto_nuclei_observations_combine_into_one_finding() -> None:
    async with background_session() as session:
        assessment, host = await _seed_multi_tool_vulnerable_host(session)
        summary = await CorrelationService(session).correlate_assessment(assessment.id)

    assert summary.hosts_evaluated == 1
    assert summary.findings_created >= 1

    async with background_session() as session:
        finding = (
            await session.execute(
                select(Finding).where(Finding.assessment_id == assessment.id, Finding.rule_id == "CROSS-002")
            )
        ).scalar_one()
        assert finding.host_id == host.id
        assert finding.severity.value == "critical"
        assert "CVE-2021-41773" in finding.title

        links = (
            await session.execute(select(FindingObservation).where(FindingObservation.finding_id == finding.id))
        ).scalars().all()
        linked_observations = (
            await session.execute(select(Observation).where(Observation.id.in_([link.observation_id for link in links])))
        ).scalars().all()
        plugins = {observation.plugin for observation in linked_observations}
        assert plugins == {"nikto", "nuclei"}, "Finding must carry evidence from both corroborating tools"
