"""Tests for the Assessment Pipeline (Phase 12).

Mirrors ``test_cross_tool_correlation.py``'s own conventions: pure rule-level
unit tests need no DB; the full end-to-end tests seed an assessment/target/
Nmap-execution/host/services directly via a real DB session (exactly the
shape ``HostInventoryService`` would have produced from a real Nmap scan)
and drive the real ``PipelineEngine`` against a real SQLite database -- no
mocking, per ``.claude/CLAUDE.md``. Neither ``nikto`` nor ``nuclei`` is
installed on this Windows dev machine, so every follow-up scanner this
suite schedules lands ``SKIPPED`` via the real, live health check --
exactly the same "tool unavailable" path a manual ``/execute`` call would
take, and still a real, meaningful assertion of the scheduling/target-
generation logic, not a fabricated success.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.core.config import get_settings
from backend.database.session import background_session
from backend.models.assessment import Assessment
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import (
    AssessmentType,
    HostState,
    HostType,
    NetworkProtocol,
    PipelineJobStatus,
    PipelineRunStatus,
    PipelineStage,
    PortState,
    TargetOrigin,
    TargetType,
    ToolExecutionStatus,
)
from backend.models.execution_host import ExecutionHost
from backend.models.observation import Observation
from backend.models.pipeline_job import PipelineJob
from backend.models.pipeline_run import PipelineRun
from backend.models.service import Service
from backend.models.target import Target
from backend.models.tool import Tool
from backend.models.tool_execution import ToolExecution
from backend.pipeline.endpoint_generator import generate_endpoint
from backend.pipeline.engine import PipelineEngine
from backend.pipeline.models import ScheduleDecision, SkipDecision
from backend.pipeline.registry import get_pipeline_rule_registry
from backend.pipeline.rules.reserved_rules import DatabaseReservedRule, SmbReservedRule, SshReservedRule
from backend.pipeline.rules.web_rules import HttpServiceRule, HttpsServiceRule
from backend.plugins.manager.plugin_manager import get_plugin_manager
from backend.workers.manager import get_execution_manager

# -- Pure rule/endpoint-generator unit tests: no DB ----------------------------


def _make_host(**overrides) -> DiscoveredHost:
    defaults = dict(
        id=uuid.uuid4(), target_id=uuid.uuid4(), assessment_id=uuid.uuid4(), hostname="example.com",
        ipv4="192.0.2.10", host_type=HostType.WEBSITE, state=HostState.UP, fingerprint="hostname:test",
        first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return DiscoveredHost(**defaults)


def _make_service(**overrides) -> Service:
    defaults = dict(
        id=uuid.uuid4(), host_id=uuid.uuid4(), port=80, protocol=NetworkProtocol.TCP, state=PortState.OPEN,
        service_name="http", fingerprint="service:test",
        first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Service(**defaults)


def test_generate_endpoint_omits_port_for_scheme_defaults() -> None:
    host = _make_host(hostname="example.com")
    assert generate_endpoint(host, _make_service(port=80), scheme="http") == "http://example.com"
    assert generate_endpoint(host, _make_service(port=443), scheme="https") == "https://example.com"


def test_generate_endpoint_includes_port_for_non_defaults() -> None:
    host = _make_host(hostname="example.com")
    assert generate_endpoint(host, _make_service(port=8080), scheme="http") == "http://example.com:8080"
    assert generate_endpoint(host, _make_service(port=8443), scheme="https") == "https://example.com:8443"


def test_https_rule_fires_before_http_rule_for_port_443() -> None:
    host = _make_host()
    service = _make_service(port=443, service_name="https")
    assert isinstance(HttpsServiceRule().evaluate(service, host), ScheduleDecision)
    assert HttpServiceRule().evaluate(service, host) is None  # not its concern -- 443 isn't an HTTP port


def test_http_rule_fires_for_port_80() -> None:
    host = _make_host()
    decision = HttpServiceRule().evaluate(_make_service(port=80, service_name="http"), host)
    assert isinstance(decision, ScheduleDecision)
    assert decision.tool_names == ("nikto", "nuclei")
    assert decision.endpoint == "http://example.com"


def test_ssh_rule_skips_with_reserved_tool_names() -> None:
    host = _make_host()
    decision = SshReservedRule().evaluate(_make_service(port=22, service_name="ssh"), host)
    assert isinstance(decision, SkipDecision)
    assert decision.reserved_tool_names == ("nikto", "nuclei")
    assert "future phase" in decision.reason


def test_smb_rule_recognizes_service_name_without_standard_port() -> None:
    host = _make_host()
    decision = SmbReservedRule().evaluate(_make_service(port=3455, service_name="microsoft-ds"), host)
    assert isinstance(decision, SkipDecision)


def test_database_rule_labels_the_known_product() -> None:
    host = _make_host()
    decision = DatabaseReservedRule().evaluate(_make_service(port=3306, service_name="mysql"), host)
    assert isinstance(decision, SkipDecision)
    assert "MySQL" in decision.reason


def test_rules_ignore_closed_ports() -> None:
    host = _make_host()
    service = _make_service(port=80, service_name="http", state=PortState.CLOSED)
    assert HttpServiceRule().evaluate(service, host) is None


def test_registry_has_no_duplicate_rule_ids() -> None:
    registry = get_pipeline_rule_registry()
    ids = [rule.rule_id for rule in registry.all_rules()]
    assert len(ids) == len(set(ids))


def test_registry_decide_returns_none_for_an_unrecognized_service() -> None:
    registry = get_pipeline_rule_registry()
    host = _make_host()
    service = _make_service(port=54321, service_name="unknown-thing")
    assert registry.decide(service, host) is None


# -- Full end-to-end: seeded Nmap results -> PipelineEngine.advance_after_nmap ---


async def _seed_assessment_with_nmap_execution(session) -> tuple[Assessment, Target, ToolExecution]:
    assessment = Assessment(name=f"pipeline-{uuid.uuid4()}", assessment_type=AssessmentType.NETWORK)
    session.add(assessment)
    await session.flush()

    target = Target(assessment_id=assessment.id, target_type=TargetType.DOMAIN, target_value="example.com")
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
    return assessment, target, nmap_execution


async def _seed_host_with_services(session, assessment, target, nmap_execution, *, hostname, services) -> DiscoveredHost:
    now = datetime.now(timezone.utc)
    host = DiscoveredHost(
        target_id=target.id, assessment_id=assessment.id, hostname=hostname, host_type=HostType.WEBSITE,
        state=HostState.UP, fingerprint=f"hostname:{hostname}", first_seen=now, last_seen=now,
        source_execution_id=nmap_execution.id,
    )
    session.add(host)
    await session.flush()
    session.add(ExecutionHost(execution_id=nmap_execution.id, host_id=host.id, is_new=True))
    for port, service_name in services:
        session.add(Service(
            host_id=host.id, port=port, protocol=NetworkProtocol.TCP, state=PortState.OPEN,
            service_name=service_name, fingerprint=f"service:{host.id}:{port}", first_seen=now, last_seen=now,
        ))
    await session.flush()
    return host


async def _make_engine(session) -> PipelineEngine:
    settings = get_settings()
    plugin_manager = get_plugin_manager(settings.plugins_dir)
    execution_manager = get_execution_manager(settings, plugin_manager)
    return PipelineEngine(session, plugin_manager, execution_manager)


@pytest.mark.asyncio
async def test_advance_after_nmap_schedules_follow_up_for_http_host(client) -> None:
    async with background_session() as session:
        assessment, target, nmap_execution = await _seed_assessment_with_nmap_execution(session)
        host = await _seed_host_with_services(
            session, assessment, target, nmap_execution, hostname="www.example.com", services=[(80, "http")]
        )
        run = PipelineRun(
            assessment_id=assessment.id, recon_execution_id=nmap_execution.id,
            status=PipelineRunStatus.RUNNING, started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        await session.flush()
        run_id = run.id

        engine = await _make_engine(session)
        await engine.advance_after_nmap(run_id, nmap_execution.id)

    async with background_session() as session:
        scan_jobs = list((
            await session.execute(
                select(PipelineJob).where(PipelineJob.pipeline_run_id == run_id, PipelineJob.stage == PipelineStage.SCAN)
            )
        ).scalars().all())
        tool_names = {job.tool_name for job in scan_jobs}
        assert tool_names == {"nikto", "nuclei"}
        assert all(job.target_value == "http://www.example.com" for job in scan_jobs)
        assert all(job.host_id == host.id for job in scan_jobs)
        # Neither tool is installed on this machine -- the real health check skips them,
        # exactly like a manual /execute call would, not a pipeline-specific shortcut.
        assert all(job.status == PipelineJobStatus.SKIPPED for job in scan_jobs)

        generated_target = (
            await session.execute(
                select(Target).where(Target.assessment_id == assessment.id, Target.target_value == "http://www.example.com")
            )
        ).scalar_one()
        assert generated_target.origin == TargetOrigin.PIPELINE
        assert generated_target.discovered_from_execution_id == nmap_execution.id

        # The scan stage is fully terminal (both SKIPPED) -- the run must have auto-finalized.
        run = await session.get(PipelineRun, run_id)
        assert run.status == PipelineRunStatus.COMPLETED
        correlate_job = (
            await session.execute(
                select(PipelineJob).where(PipelineJob.pipeline_run_id == run_id, PipelineJob.stage == PipelineStage.CORRELATE)
            )
        ).scalar_one()
        assert correlate_job.status == PipelineJobStatus.COMPLETED


@pytest.mark.asyncio
async def test_advance_after_nmap_records_observation_and_skip_for_ssh_only_host(client) -> None:
    async with background_session() as session:
        assessment, target, nmap_execution = await _seed_assessment_with_nmap_execution(session)
        host = await _seed_host_with_services(
            session, assessment, target, nmap_execution, hostname="ssh-only.example.com", services=[(22, "ssh")]
        )
        run = PipelineRun(
            assessment_id=assessment.id, recon_execution_id=nmap_execution.id,
            status=PipelineRunStatus.RUNNING, started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        await session.flush()
        run_id, host_id = run.id, host.id

        engine = await _make_engine(session)
        await engine.advance_after_nmap(run_id, nmap_execution.id)

    async with background_session() as session:
        scan_jobs = list((
            await session.execute(
                select(PipelineJob).where(PipelineJob.pipeline_run_id == run_id, PipelineJob.stage == PipelineStage.SCAN)
            )
        ).scalars().all())
        assert {job.tool_name for job in scan_jobs} == {"nikto", "nuclei"}
        assert all(job.status == PipelineJobStatus.SKIPPED for job in scan_jobs)
        assert all("SSH" in job.skip_reason for job in scan_jobs)

        # No synthetic endpoint target was ever created for a non-web service.
        pipeline_targets = list((
            await session.execute(select(Target).where(Target.discovered_from_execution_id == nmap_execution.id))
        ).scalars().all())
        assert pipeline_targets == []

        observation = (
            await session.execute(select(Observation).where(Observation.host_id == host_id, Observation.plugin == "pipeline-engine"))
        ).scalar_one()
        assert "SSH" in observation.title


@pytest.mark.asyncio
async def test_advance_after_nmap_host_with_no_web_service_gets_generic_skip(client) -> None:
    async with background_session() as session:
        assessment, target, nmap_execution = await _seed_assessment_with_nmap_execution(session)
        await _seed_host_with_services(
            session, assessment, target, nmap_execution, hostname="quiet.example.com", services=[]
        )
        run = PipelineRun(
            assessment_id=assessment.id, recon_execution_id=nmap_execution.id,
            status=PipelineRunStatus.RUNNING, started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        await session.flush()
        run_id = run.id

        engine = await _make_engine(session)
        await engine.advance_after_nmap(run_id, nmap_execution.id)

    async with background_session() as session:
        scan_jobs = list((
            await session.execute(
                select(PipelineJob).where(PipelineJob.pipeline_run_id == run_id, PipelineJob.stage == PipelineStage.SCAN)
            )
        ).scalars().all())
        assert {job.tool_name for job in scan_jobs} == {"nikto", "nuclei"}
        assert all(job.skip_reason == "No supported web services discovered." for job in scan_jobs)


@pytest.mark.asyncio
async def test_advance_after_recon_failure_skips_follow_up_with_reason(client) -> None:
    async with background_session() as session:
        assessment, target, nmap_execution = await _seed_assessment_with_nmap_execution(session)
        run = PipelineRun(
            assessment_id=assessment.id, recon_execution_id=nmap_execution.id,
            status=PipelineRunStatus.RUNNING, started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        await session.flush()
        run_id = run.id

        engine = await _make_engine(session)
        await engine.advance_after_recon_failure(run_id)

    async with background_session() as session:
        run = await session.get(PipelineRun, run_id)
        assert run.status == PipelineRunStatus.FAILED
        scan_jobs = list((
            await session.execute(
                select(PipelineJob).where(PipelineJob.pipeline_run_id == run_id, PipelineJob.stage == PipelineStage.SCAN)
            )
        ).scalars().all())
        assert len(scan_jobs) == 2
        assert all(job.status == PipelineJobStatus.SKIPPED for job in scan_jobs)
        assert all("Nmap did not complete" in job.skip_reason for job in scan_jobs)


@pytest.mark.asyncio
async def test_advance_after_nmap_is_idempotent_on_a_second_run(client) -> None:
    """Re-running the pipeline against the same host must reuse the synthetic target, not duplicate it."""
    async with background_session() as session:
        assessment, target, nmap_execution = await _seed_assessment_with_nmap_execution(session)
        await _seed_host_with_services(
            session, assessment, target, nmap_execution, hostname="repeat.example.com", services=[(443, "https")]
        )
        run = PipelineRun(
            assessment_id=assessment.id, recon_execution_id=nmap_execution.id,
            status=PipelineRunStatus.RUNNING, started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        await session.flush()
        run_id = run.id
        engine = await _make_engine(session)
        await engine.advance_after_nmap(run_id, nmap_execution.id)

    # A second, independent pipeline run against the same assessment/host.
    async with background_session() as session:
        run2 = PipelineRun(
            assessment_id=assessment.id, recon_execution_id=nmap_execution.id,
            status=PipelineRunStatus.RUNNING, started_at=datetime.now(timezone.utc),
        )
        session.add(run2)
        await session.flush()
        run2_id = run2.id
        engine = await _make_engine(session)
        await engine.advance_after_nmap(run2_id, nmap_execution.id)

    async with background_session() as session:
        targets = list((
            await session.execute(
                select(Target).where(Target.assessment_id == assessment.id, Target.target_value == "https://repeat.example.com")
            )
        ).scalars().all())
        assert len(targets) == 1, "the synthetic endpoint target must be reused, not duplicated, across pipeline runs"


@pytest.mark.asyncio
async def test_get_pipeline_shows_live_running_status_before_the_job_terminates(client) -> None:
    """Regression test: a job's PipelineJob.status is only re-stamped at its execution's
    *terminal* transition (see backend.workers.pipeline_hook) -- nothing re-stamps it on a mere
    PREPARING -> RUNNING transition. GET /assessments/{id}/pipeline must still show "running" for
    a job whose real execution is running, not "waiting" for the job's entire, possibly
    multi-minute duration. Caught live: the real Nmap recon job stayed "waiting" in the UI for
    the ~3 minutes its scan actually ran, only flipping to "completed" at the very end.
    """
    async with background_session() as session:
        assessment, target, nmap_execution = await _seed_assessment_with_nmap_execution(session)
        run = PipelineRun(
            assessment_id=assessment.id, recon_execution_id=nmap_execution.id,
            status=PipelineRunStatus.RUNNING, started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        await session.flush()
        run_id = run.id
        session.add(
            PipelineJob(
                pipeline_run_id=run_id, stage=PipelineStage.RECON, tool_name="nmap",
                execution_id=nmap_execution.id, target_value=target.target_value,
                status=PipelineJobStatus.WAITING,  # stamped at plan time, while the job was still PENDING
            )
        )
        # The underlying execution has since moved on to RUNNING -- nothing re-stamps the
        # PipelineJob row for a non-terminal transition.
        nmap_execution.status = ToolExecutionStatus.RUNNING
        assessment_id = assessment.id

    response = await client.get(f"/api/v1/assessments/{assessment_id}/pipeline")
    assert response.status_code == 200, response.text
    recon_job = next(job for job in response.json()["jobs"] if job["stage"] == "recon")
    assert recon_job["status"] == "running"


@pytest.mark.asyncio
async def test_pipeline_generated_targets_are_excluded_from_assessment_target_count(client) -> None:
    """Regression test: Assessment.target_count (and the Targets tab it backs, and the Dashboard's
    own 'targets' overview stat) must reflect what the user actually added, not be inflated by
    every synthetic endpoint target (e.g. 'http://host:80') the Assessment Pipeline generates.
    Caught live: after one real pipeline run against a single user target, the Targets tab's own
    header showed "Targets (5)" while the list beneath it -- correctly filtered -- showed only 1.
    """
    async with background_session() as session:
        assessment, target, nmap_execution = await _seed_assessment_with_nmap_execution(session)
        await _seed_host_with_services(
            session, assessment, target, nmap_execution, hostname="count-check.example.com",
            services=[(80, "http"), (443, "https")],
        )
        run = PipelineRun(
            assessment_id=assessment.id, recon_execution_id=nmap_execution.id,
            status=PipelineRunStatus.RUNNING, started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        await session.flush()
        run_id = run.id
        assessment_id = assessment.id
        engine = await _make_engine(session)
        await engine.advance_after_nmap(run_id, nmap_execution.id)

    # Two synthetic endpoint targets (http/https) were generated on top of the one user target.
    async with background_session() as session:
        all_targets = list((
            await session.execute(select(Target).where(Target.assessment_id == assessment_id))
        ).scalars().all())
        assert len(all_targets) == 3

    response = await client.get(f"/api/v1/assessments/{assessment_id}")
    assert response.status_code == 200, response.text
    assert response.json()["target_count"] == 1
