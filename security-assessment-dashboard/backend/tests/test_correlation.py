"""Tests for the Correlation Engine and Intelligence Dashboard (Phase 9).

Deliberately independent of any real security tool (unlike
``test_host_inventory.py``'s Nmap-dependent integration tests): every host/
service/technology/observation this file needs is inserted directly via a
real DB session, exactly the shape :class:`~backend.services.host_inventory_service.HostInventoryService`
would have produced -- so these tests run identically whether or not Nmap is
installed on the machine running them, while still exercising the real
:class:`~backend.services.correlation_service.CorrelationService` against a
real SQLite database (no mocking, per ``.claude/CLAUDE.md``).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.correlation.models import RuleContext
from backend.correlation.rules.service_rules import SmbServiceExposedRule, TelnetServiceExposedRule
from backend.correlation.rules.ssh_rules import WeakSshAlgorithmsRule
from backend.database.session import background_session
from backend.models.assessment import Assessment
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import (
    AssessmentType,
    FindingConfidence,
    HostState,
    HostType,
    NetworkProtocol,
    ObservationCategory,
    PortState,
    TargetType,
    ToolExecutionStatus,
)
from backend.models.execution_host import ExecutionHost
from backend.models.execution_observation import ExecutionObservation
from backend.models.finding import Finding
from backend.models.observation import Observation
from backend.models.service import Service
from backend.models.target import Target
from backend.models.tool import Tool
from backend.models.tool_execution import ToolExecution
from backend.services import fingerprinting
from backend.services.correlation_service import CorrelationService

# -- Rule unit tests: pure, no DB --------------------------------------------


def _empty_context(host: DiscoveredHost) -> RuleContext:
    return RuleContext(host=host, services=[], technologies=[], operating_systems=[], observations=[])


def _make_host(**overrides) -> DiscoveredHost:
    defaults = dict(
        id=uuid.uuid4(), target_id=uuid.uuid4(), assessment_id=uuid.uuid4(), hostname="host", ipv4="10.0.0.1",
        host_type=HostType.HOST, state=HostState.UP, fingerprint="ipv4:test",
        first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return DiscoveredHost(**defaults)


def _make_service(host: DiscoveredHost, **overrides) -> Service:
    defaults = dict(
        id=uuid.uuid4(), host_id=host.id, port=80, protocol=NetworkProtocol.TCP, state=PortState.OPEN,
        fingerprint="service:test", first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Service(**defaults)


def test_telnet_rule_fires_on_open_telnet_port() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.services = [_make_service(host, port=23, service_name="telnet")]
    candidates = TelnetServiceExposedRule().evaluate(context)
    assert len(candidates) == 1
    assert "23" in candidates[0].detail


def test_telnet_rule_does_not_fire_without_telnet() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.services = [_make_service(host, port=80, service_name="http")]
    assert TelnetServiceExposedRule().evaluate(context) == []


def test_telnet_rule_ignores_closed_port() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.services = [_make_service(host, port=23, service_name="telnet", state=PortState.CLOSED)]
    assert TelnetServiceExposedRule().evaluate(context) == []


def test_smb_rule_merges_both_smb_ports_into_one_candidate() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.services = [
        _make_service(host, port=139, service_name="netbios-ssn"),
        _make_service(host, port=445, service_name="microsoft-ds"),
    ]
    candidates = SmbServiceExposedRule().evaluate(context)
    assert len(candidates) == 1
    assert len(candidates[0].matched_services) == 2


def test_ssh_weak_algorithms_rule_matches_known_weak_algorithm() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.observations = [
        Observation(
            id=uuid.uuid4(), host_id=host.id, plugin="nmap", source="ssh2-enum-algos", category=ObservationCategory.AUTH,
            title="ssh2-enum-algos", detail="encryption_algorithms: aes128-cbc, arcfour256",
            fingerprint="observation:test", first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
        )
    ]
    candidates = WeakSshAlgorithmsRule().evaluate(context)
    assert len(candidates) == 1
    assert "cbc" in candidates[0].detail.lower() or "arcfour256" in candidates[0].detail.lower()


def test_ssh_weak_algorithms_rule_does_not_fire_on_strong_algorithms_only() -> None:
    host = _make_host()
    context = _empty_context(host)
    context.observations = [
        Observation(
            id=uuid.uuid4(), host_id=host.id, plugin="nmap", source="ssh2-enum-algos", category=ObservationCategory.AUTH,
            title="ssh2-enum-algos", detail="encryption_algorithms: chacha20-poly1305@openssh.com, aes256-gcm@openssh.com",
            fingerprint="observation:test", first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
        )
    ]
    assert WeakSshAlgorithmsRule().evaluate(context) == []


# -- Fingerprint unit test ----------------------------------------------------


def test_finding_fingerprint_is_deterministic_and_scoped_by_rule_and_host() -> None:
    a = fingerprinting.finding_fingerprint(rule_id="SVC-001", host_fingerprint_value="ipv4:abc")
    b = fingerprinting.finding_fingerprint(rule_id="SVC-001", host_fingerprint_value="ipv4:abc")
    c = fingerprinting.finding_fingerprint(rule_id="SVC-002", host_fingerprint_value="ipv4:abc")
    d = fingerprinting.finding_fingerprint(rule_id="SVC-001", host_fingerprint_value="ipv4:xyz")
    assert a == b
    assert a != c
    assert a != d


# -- CorrelationService integration tests: real DB, no real scanner ---------


async def _seed_assessment_with_host(session, *, telnet: bool = True) -> tuple[Assessment, DiscoveredHost, Tool]:
    assessment = Assessment(name=f"corr-{uuid.uuid4()}", assessment_type=AssessmentType.NETWORK)
    session.add(assessment)
    await session.flush()

    target = Target(assessment_id=assessment.id, target_type=TargetType.IPV4, target_value="10.10.10.10")
    session.add(target)
    tool = (await session.execute(select(Tool).where(Tool.name == "nmap"))).scalar_one_or_none()
    if tool is None:
        tool = Tool(name="nmap", display_name="Nmap")
        session.add(tool)
    await session.flush()

    execution = ToolExecution(
        assessment_id=assessment.id, target_id=target.id, tool_id=tool.id, status=ToolExecutionStatus.COMPLETED
    )
    session.add(execution)
    await session.flush()

    now = datetime.now(timezone.utc)
    host_fp = fingerprinting.host_fingerprint(mac_address=None, ipv4="10.10.10.10", ipv6=None, hostname=None)
    host = DiscoveredHost(
        target_id=target.id, assessment_id=assessment.id, hostname="corr-host", ipv4="10.10.10.10", host_type=HostType.HOST,
        state=HostState.UP, fingerprint=host_fp, first_seen=now, last_seen=now, source_execution_id=execution.id,
    )
    session.add(host)
    await session.flush()
    session.add(ExecutionHost(execution_id=execution.id, host_id=host.id, is_new=True))

    if telnet:
        service_fp = fingerprinting.service_fingerprint(host_fingerprint_value=host_fp, port=23, protocol=NetworkProtocol.TCP)
        session.add(
            Service(
                host_id=host.id, port=23, protocol=NetworkProtocol.TCP, state=PortState.OPEN, service_name="telnet",
                fingerprint=service_fp, first_seen=now, last_seen=now,
            )
        )
    await session.flush()
    return assessment, host, tool


@pytest.mark.asyncio
async def test_correlate_assessment_creates_finding_from_open_telnet() -> None:
    async with background_session() as session:
        assessment, host, _tool = await _seed_assessment_with_host(session)
        summary = await CorrelationService(session).correlate_assessment(assessment.id)

    assert summary.hosts_evaluated == 1
    assert summary.findings_created >= 1

    async with background_session() as session:
        rows = (
            await session.execute(select(Finding).where(Finding.assessment_id == assessment.id, Finding.rule_id == "SVC-001"))
        ).scalars().all()
        assert len(rows) == 1
        finding = rows[0]
        assert finding.severity.value == "high"
        assert finding.host_id == host.id
        assert finding.plugin == "nmap"


@pytest.mark.asyncio
async def test_correlate_assessment_is_idempotent_no_duplicate_findings() -> None:
    async with background_session() as session:
        assessment, _host, _tool = await _seed_assessment_with_host(session)
        first = await CorrelationService(session).correlate_assessment(assessment.id)
    async with background_session() as session:
        second = await CorrelationService(session).correlate_assessment(assessment.id)

    assert first.findings_created >= 1
    assert second.findings_created == 0
    assert second.findings_updated == first.findings_created

    async with background_session() as session:
        count = (
            await session.execute(
                select(func.count()).select_from(Finding).where(Finding.assessment_id == assessment.id, Finding.rule_id == "SVC-001")
            )
        ).scalar_one()
        assert count == 1  # never duplicated across repeated runs


@pytest.mark.asyncio
async def test_correlate_assessment_produces_no_findings_when_nothing_matches() -> None:
    async with background_session() as session:
        assessment, _host, _tool = await _seed_assessment_with_host(session, telnet=False)
        summary = await CorrelationService(session).correlate_assessment(assessment.id)
    # GEN-001/CONFIG-002 etc. require product/version banners or >=8 ports, neither present here.
    assert summary.findings_created == 0


@pytest.mark.asyncio
async def test_confidence_increases_with_multiple_supporting_observations_and_executions() -> None:
    """Re-confirming the same weak-SSH observation across two distinct executions should raise confidence above base."""
    async with background_session() as session:
        assessment, host, tool = await _seed_assessment_with_host(session, telnet=False)
        now = datetime.now(timezone.utc)

        target = (await session.execute(select(Target).where(Target.assessment_id == assessment.id))).scalar_one()
        execution_2 = ToolExecution(assessment_id=assessment.id, target_id=target.id, tool_id=tool.id, status=ToolExecutionStatus.COMPLETED)
        session.add(execution_2)
        await session.flush()

        host_fp = host.fingerprint
        observation_fp = fingerprinting.observation_fingerprint(
            plugin="nmap", host_fingerprint_value=host_fp, category="auth", observation_type="ssh2-enum-algos", title="ssh2-enum-algos"
        )
        observation = Observation(
            host_id=host.id, plugin="nmap", source="ssh2-enum-algos", category=ObservationCategory.AUTH,
            observation_type="ssh2-enum-algos", title="ssh2-enum-algos", detail="mac_algorithms: hmac-md5, hmac-sha2-256",
            fingerprint=observation_fp, first_seen=now, last_seen=now,
        )
        session.add(observation)
        await session.flush()
        session.add(ExecutionObservation(execution_id=host.source_execution_id, observation_id=observation.id, is_new=True))
        session.add(ExecutionObservation(execution_id=execution_2.id, observation_id=observation.id, is_new=False))
        await session.flush()

        await CorrelationService(session).correlate_assessment(assessment.id)

    async with background_session() as session:
        finding = (
            await session.execute(select(Finding).where(Finding.assessment_id == assessment.id, Finding.rule_id == "SSH-001"))
        ).scalar_one()
        base = WeakSshAlgorithmsRule().base_confidence
        order = [FindingConfidence.LOW, FindingConfidence.MEDIUM, FindingConfidence.HIGH, FindingConfidence.CONFIRMED]
        assert order.index(finding.confidence) > order.index(base)


# -- API integration: findings, correlation, dashboard -----------------------


@pytest.mark.asyncio
async def test_correlation_run_endpoint_and_findings_and_dashboard_reflect_it(client: AsyncClient) -> None:
    async with background_session() as session:
        assessment, _host, _tool = await _seed_assessment_with_host(session)

    run_response = await client.post("/api/v1/correlation/run", json={"assessment_id": str(assessment.id)})
    assert run_response.status_code == 200
    run_body = run_response.json()
    assert run_body["findings_created"] >= 1
    assert run_body["hosts_evaluated"] == 1

    status_response = await client.get("/api/v1/correlation/status")
    assert status_response.status_code == 200
    assert status_response.json()["registered_rule_count"] > 0
    assert status_response.json()["last_run"] is not None

    findings_response = await client.get("/api/v1/findings", params={"assessment_id": str(assessment.id)})
    assert findings_response.status_code == 200
    findings_body = findings_response.json()
    assert findings_body["total"] >= 1
    finding_id = findings_body["items"][0]["id"]

    detail_response = await client.get(f"/api/v1/findings/{finding_id}")
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["host"] is not None
    assert isinstance(detail_body["evidence"], list) and len(detail_body["evidence"]) >= 1
    assert isinstance(detail_body["references"], list) and len(detail_body["references"]) >= 1

    severity_filtered = await client.get(
        "/api/v1/findings", params={"assessment_id": str(assessment.id), "severity": "high"}
    )
    assert severity_filtered.status_code == 200
    assert all(item["severity"] == "high" for item in severity_filtered.json()["items"])

    dashboard_response = await client.get("/api/v1/dashboard", params={"assessment_id": str(assessment.id)})
    assert dashboard_response.status_code == 200
    dashboard_body = dashboard_response.json()
    assert dashboard_body["is_empty"] is False
    assert dashboard_body["overview"]["findings"] >= 1
    assert dashboard_body["overview"]["hosts_discovered"] == 1
    assert dashboard_body["overview"]["targets"] >= 1
    assert sum(dashboard_body["security_summary"].values()) == dashboard_body["overview"]["findings"]

    stats_response = await client.get("/api/v1/statistics", params={"assessment_id": str(assessment.id)})
    assert stats_response.status_code == 200
    assert stats_response.json()["overview"]["findings"] == dashboard_body["overview"]["findings"]


@pytest.mark.asyncio
async def test_deleted_assessment_data_is_excluded_from_dashboard_hosts_findings_and_search(client: AsyncClient) -> None:
    """A soft-deleted assessment's hosts/findings must vanish from every read view, not just the assessment list.

    ``AssessmentService.delete()`` only sets ``deleted_at`` -- it never
    removes the row or cascades (see that method's own docstring) -- so this
    is a regression test for every read-side query that has to filter
    ``deleted_at`` out itself: the workspace-wide dashboard, host list,
    findings list, and global search.
    """
    async with background_session() as session:
        assessment, host, _tool = await _seed_assessment_with_host(session)
        assessment_id = assessment.id
        await CorrelationService(session).correlate_assessment(assessment_id)

    before_dashboard = (await client.get("/api/v1/dashboard")).json()
    assert before_dashboard["overview"]["hosts_discovered"] >= 1
    assert before_dashboard["overview"]["findings"] >= 1

    before_hosts = (await client.get("/api/v1/hosts")).json()
    assert any(h["id"] == str(host.id) for h in before_hosts["items"])

    before_findings = (await client.get("/api/v1/findings")).json()
    assert any(f["host_id"] == str(host.id) for f in before_findings["items"] if f.get("host_id"))

    before_search = (await client.get("/api/v1/search", params={"q": "corr-host"})).json()
    assert any(h["id"] == str(host.id) for h in before_search["hosts"])

    delete_response = await client.delete(f"/api/v1/assessments/{assessment_id}")
    assert delete_response.status_code == 204

    after_dashboard = (await client.get("/api/v1/dashboard")).json()
    assert after_dashboard["overview"]["hosts_discovered"] == before_dashboard["overview"]["hosts_discovered"] - 1
    assert after_dashboard["overview"]["findings"] < before_dashboard["overview"]["findings"]

    after_hosts = (await client.get("/api/v1/hosts")).json()
    assert not any(h["id"] == str(host.id) for h in after_hosts["items"])

    after_findings = (await client.get("/api/v1/findings")).json()
    assert not any(f["host_id"] == str(host.id) for f in after_findings["items"] if f.get("host_id"))

    after_search = (await client.get("/api/v1/search", params={"q": "corr-host"})).json()
    assert not any(h["id"] == str(host.id) for h in after_search["hosts"])

    scoped_dashboard = await client.get("/api/v1/dashboard", params={"assessment_id": str(assessment_id)})
    assert scoped_dashboard.status_code == 200
    assert scoped_dashboard.json()["overview"]["hosts_discovered"] == 0


@pytest.mark.asyncio
async def test_correlate_same_host_fingerprint_across_two_targets_creates_separate_findings() -> None:
    """Two different Assessment Targets that happen to discover the same IP must never merge findings.

    Regression test for the bug fixed by ``a1b2c3d4e5f6``: the Finding
    upsert used to key only on ``(assessment_id, fingerprint)``, and
    ``fingerprint`` is derived from host identity (IP/MAC/hostname) alone --
    not target-scoped. Two ``DiscoveredHost`` rows under two different
    ``Target``s with the same IP produce the same ``fingerprint``; before the
    fix, correlating the second host found the first host's ``Finding`` row
    and silently merged onto it.
    """
    now = datetime.now(timezone.utc)
    async with background_session() as session:
        assessment = Assessment(name=f"cross-target-{uuid.uuid4()}", assessment_type=AssessmentType.NETWORK)
        session.add(assessment)
        await session.flush()

        tool = (await session.execute(select(Tool).where(Tool.name == "nmap"))).scalar_one_or_none()
        if tool is None:
            tool = Tool(name="nmap", display_name="Nmap")
            session.add(tool)
            await session.flush()

        host_fp = fingerprinting.host_fingerprint(mac_address=None, ipv4="192.168.1.20", ipv6=None, hostname=None)
        hosts = []
        for target_value in ("192.168.1.20", "192.168.1.0/24"):
            target_type = TargetType.IPV4 if "/" not in target_value else TargetType.CIDR
            target = Target(assessment_id=assessment.id, target_type=target_type, target_value=target_value)
            session.add(target)
            await session.flush()

            execution = ToolExecution(
                assessment_id=assessment.id, target_id=target.id, tool_id=tool.id, status=ToolExecutionStatus.COMPLETED
            )
            session.add(execution)
            await session.flush()

            host = DiscoveredHost(
                target_id=target.id, assessment_id=assessment.id, hostname=None, ipv4="192.168.1.20",
                host_type=HostType.HOST, state=HostState.UP, fingerprint=host_fp, first_seen=now, last_seen=now,
                source_execution_id=execution.id,
            )
            session.add(host)
            await session.flush()
            session.add(ExecutionHost(execution_id=execution.id, host_id=host.id, is_new=True))

            service_fp = fingerprinting.service_fingerprint(host_fingerprint_value=host_fp, port=23, protocol=NetworkProtocol.TCP)
            session.add(
                Service(
                    host_id=host.id, port=23, protocol=NetworkProtocol.TCP, state=PortState.OPEN, service_name="telnet",
                    fingerprint=service_fp, first_seen=now, last_seen=now,
                )
            )
            await session.flush()
            hosts.append(host)

        assert hosts[0].fingerprint == hosts[1].fingerprint  # same IP, genuinely colliding host identity
        assert hosts[0].id != hosts[1].id  # but two distinct hosts (two distinct targets)

        summary = await CorrelationService(session).correlate_assessment(assessment.id)

    assert summary.hosts_evaluated == 2
    assert summary.findings_created == 2  # one per host, not merged into one

    async with background_session() as session:
        findings = (
            await session.execute(select(Finding).where(Finding.assessment_id == assessment.id, Finding.rule_id == "SVC-001"))
        ).scalars().all()
        assert len(findings) == 2
        assert {f.host_id for f in findings} == {hosts[0].id, hosts[1].id}


@pytest.mark.asyncio
async def test_dashboard_empty_state_for_assessment_with_no_data(client: AsyncClient) -> None:
    async with background_session() as session:
        assessment = Assessment(name=f"empty-{uuid.uuid4()}", assessment_type=AssessmentType.NETWORK)
        session.add(assessment)
        await session.flush()
        empty_assessment_id = assessment.id

    response = await client.get("/api/v1/dashboard", params={"assessment_id": str(empty_assessment_id)})
    assert response.status_code == 200
    body = response.json()
    assert body["is_empty"] is True
    assert body["overview"]["hosts_discovered"] == 0
    assert body["overview"]["findings"] == 0
    assert body["finding_dashboard"]["newest"] == []
