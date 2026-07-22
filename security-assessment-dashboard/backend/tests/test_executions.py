"""Tests for the Assessment Execution Engine (Phase 6).

Exercises the whole engine -- planning, queuing, concurrency, cancellation,
retry, logging, and progress reporting -- against the real HTTP API and a
real (SQLite) database, using ``dummy-execution``
(``backend/plugins/plugins/dummy_execution``) as the only "tool": a
plugin that never starts an external program, so these tests are fast
and host-independent. Per this phase's explicit instruction ("Do NOT
integrate Nmap ... Only verify using DummyExecutionPlugin"), no real
security tool is exercised here.
"""

import asyncio
import time
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.core.config import get_settings
from backend.database.session import background_session
from backend.models.enums import ToolExecutionStatus as S
from backend.models.enums import ToolStatus
from backend.models.tool import Tool
from backend.plugins.manager.plugin_manager import get_plugin_manager
from backend.workers.queue import ExecutionQueue
from backend.workers.state import is_transition_allowed

DUMMY_TOOL_NAME = "dummy-execution"

# Each test's `client` fixture drives the FastAPI app's real lifespan
# (backend.main.lifespan), which now calls shutdown_execution_manager() on
# exit -- so every test starts from a freshly constructed ExecutionManager,
# bound to that test's own event loop (pytest.ini scopes one per test
# function). No manual singleton reset needed here.


async def _ensure_dummy_tool_row() -> None:
    """Create a minimal ``Tool`` catalog row for the test-only dummy plugin.

    ``dummy-execution`` is deliberately excluded from
    ``ToolService.SUPPORTED_TOOL_IDS`` (it must never appear in Tool
    Management), so nothing ever syncs a catalog row for it the way
    ``POST /tools/discover`` does for the 15 real tools. A job's
    ``tool_id`` foreign key still requires one to exist.
    """
    async with background_session() as session:
        existing = (await session.execute(select(Tool).where(Tool.name == DUMMY_TOOL_NAME))).scalar_one_or_none()
        if existing is None:
            session.add(
                Tool(
                    name=DUMMY_TOOL_NAME,
                    display_name="Dummy Execution Plugin",
                    status=ToolStatus.INSTALLED,
                    is_installed=True,
                    enabled=True,
                )
            )


def _dummy_plugin_config():
    """The live, in-memory ``PluginConfiguration`` the execution engine reads for this plugin."""
    manager = get_plugin_manager(get_settings().plugins_dir)
    return manager.get_plugin(DUMMY_TOOL_NAME).config


async def _create_assessment(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/assessments",
        json={"name": f"Execution-tests-{uuid.uuid4().hex[:8]}", "assessment_type": "network", "tags": []},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _add_target(client: AsyncClient, assessment_id: str, value: str = "10.10.10.10") -> str:
    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets", json={"target_type": "ipv4", "target_value": value}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _wait_for_status(client: AsyncClient, job_id: str, expected: set[str], *, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        response = await client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in expected:
            return body
        if time.monotonic() > deadline:
            raise AssertionError(f"Job {job_id} did not reach {expected} within {timeout}s (last: {body['status']})")
        await asyncio.sleep(0.03)


async def _wait_for_assessment_status(client: AsyncClient, assessment_id: str, expected: str, *, timeout: float = 5.0) -> dict:
    """Poll an assessment until its status settles, instead of reading it once.

    A job reaching a terminal status and the assessment-level status revert
    that follows it are two *separate* commits a few awaits apart
    (ExecutionManager._finalize() writes the job's row, publishes an event,
    then _on_job_terminal()/_finalize_assessment() writes the assessment's
    row) -- there is no atomicity across them from an external caller's
    point of view. Asserting on a single immediate read right after the job
    reaches its terminal status is a real, if narrow, race: under load, that
    read can land in the gap before the assessment's own commit. Observed
    directly while stress-testing the execution engine -- reproducible often
    enough under repeated full-suite runs to not be a fluke.
    """
    deadline = time.monotonic() + timeout
    while True:
        response = await client.get(f"/api/v1/assessments/{assessment_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] == expected:
            return body
        if time.monotonic() > deadline:
            raise AssertionError(
                f"Assessment {assessment_id} did not reach status {expected!r} within {timeout}s (last: {body['status']!r})"
            )
        await asyncio.sleep(0.03)


# -- Unit tests: ExecutionQueue --------------------------------------------------


@pytest.mark.asyncio
async def test_queue_dequeues_in_priority_then_fifo_order() -> None:
    queue = ExecutionQueue()
    first, second, retry = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await queue.enqueue(first, priority=100)
    await queue.enqueue(second, priority=100)
    await queue.enqueue(retry, priority=0)  # retry priority jumps ahead of fresh jobs

    assert await queue.dequeue() == retry
    assert await queue.dequeue() == first
    assert await queue.dequeue() == second


@pytest.mark.asyncio
async def test_queue_skips_jobs_cancelled_before_dequeue() -> None:
    queue = ExecutionQueue()
    keep, cancel = uuid.uuid4(), uuid.uuid4()
    await queue.enqueue(cancel)
    await queue.enqueue(keep)
    queue.cancel_queued(cancel)

    assert await queue.dequeue() == keep


# -- Unit tests: job state machine ------------------------------------------------


def test_state_transitions_allow_retry_from_every_retriable_status() -> None:
    assert is_transition_allowed(S.FAILED, S.QUEUED)
    assert is_transition_allowed(S.CANCELLED, S.QUEUED)
    assert is_transition_allowed(S.TIMEOUT, S.QUEUED)


def test_state_transitions_forbid_leaving_terminal_non_retriable_statuses() -> None:
    assert not is_transition_allowed(S.COMPLETED, S.QUEUED)
    assert not is_transition_allowed(S.SKIPPED, S.QUEUED)


# -- Integration tests: the full engine via the HTTP API --------------------------


@pytest.mark.asyncio
async def test_execute_plans_and_completes_jobs(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:0.05"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id, "10.0.0.1")
    await _add_target(client, assessment_id, "10.0.0.2")

    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["queued_count"] == 2
    assert body["skipped_count"] == 0

    for job in body["jobs"]:
        finished = await _wait_for_status(client, job["id"], {"completed"})
        assert finished["return_code"] == 0
        assert finished["duration"] is not None

    progress = (await client.get(f"/api/v1/assessments/{assessment_id}/progress")).json()
    assert progress["completed"] == 2
    assert progress["percent_complete"] == 100.0

    await _wait_for_assessment_status(client, assessment_id, "completed")


@pytest.mark.asyncio
async def test_execute_skips_disabled_tool(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    config = _dummy_plugin_config()
    config.enabled = False
    try:
        assessment_id = await _create_assessment(client)
        await _add_target(client, assessment_id)

        response = await client.post(
            f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]}
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["queued_count"] == 0
        assert body["skipped_count"] == 1
        assert body["jobs"][0]["status"] == "skipped"
        assert "disabled" in body["jobs"][0]["status_message"]
    finally:
        config.enabled = True


@pytest.mark.asyncio
async def test_execute_unknown_tool_returns_404(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": ["not-a-real-tool"]}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_job_failure_via_nonzero_exit_code(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:0.05", "fail"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]

    finished = await _wait_for_status(client, job_id, {"failed"})
    assert finished["return_code"] == 1
    assert "Exit code 1" in finished["status_message"]


@pytest.mark.asyncio
async def test_failed_job_with_partial_output_still_persists_raw_output(client: AsyncClient) -> None:
    """A non-zero exit must not discard real output the tool already produced.

    Regression test for a real bug: ``_execute_job`` used to gate
    ``_persist_scan_results`` on ``exit_code == 0``, so a tool that exited
    non-zero after already emitting a genuine partial report (e.g. Nikto
    hitting its own error-rate limit mid-scan) silently lost that output --
    a worse violation of "only display real collected data" than persisting
    it under a job still honestly marked ``failed``.
    """
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:0.05", "fail-with-output"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]

    finished = await _wait_for_status(client, job_id, {"failed"})
    assert finished["return_code"] == 1

    raw_output = await client.get(f"/api/v1/jobs/{job_id}/raw-output")
    assert raw_output.status_code == 200, raw_output.text
    assert "partial dummy scan of" in raw_output.json()["content"]


@pytest.mark.asyncio
async def test_failed_job_with_no_output_records_nothing(client: AsyncClient) -> None:
    """The companion case: a non-zero exit with truly empty stdout persists nothing."""
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:0.05", "fail"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]

    await _wait_for_status(client, job_id, {"failed"})

    raw_output = await client.get(f"/api/v1/jobs/{job_id}/raw-output")
    assert raw_output.status_code == 404


@pytest.mark.asyncio
async def test_job_failure_via_exception(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:0.05", "raise"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]

    finished = await _wait_for_status(client, job_id, {"failed"})
    assert "simulated crash" in finished["status_message"]


@pytest.mark.asyncio
async def test_cancel_running_job_and_assessment_reverts_status(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:2.0"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]

    running = await _wait_for_status(client, job_id, {"running"})
    assert running["started_at"] is not None

    cancel_response = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_response.status_code == 200

    finished = await _wait_for_status(client, job_id, {"cancelled"})
    assert "cancelled" in finished["status_message"].lower()

    await _wait_for_assessment_status(client, assessment_id, "draft")  # reverted to its pre-run status, not left "running"


@pytest.mark.asyncio
async def test_cancel_queued_job_before_it_starts(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:1.0"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]

    # Cancel immediately -- whether this catches the job still QUEUED or
    # already RUNNING is a race, but ExecutionManager.cancel() handles
    # both branches and either way it must end up CANCELLED quickly.
    cancel_response = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_response.status_code == 200
    await _wait_for_status(client, job_id, {"cancelled"})


@pytest.mark.asyncio
async def test_cancel_terminal_job_is_rejected(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:0.05"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]
    await _wait_for_status(client, job_id, {"completed"})

    cancel_response = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_response.status_code == 409


@pytest.mark.asyncio
async def test_retry_failed_job_succeeds_after_reconfiguration(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    config = _dummy_plugin_config()
    config.arguments = ["duration:0.05", "fail"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]
    failed = await _wait_for_status(client, job_id, {"failed"})
    assert failed["retry_count"] == 0

    config.arguments = ["duration:0.05"]  # fix the "misconfiguration" before retrying
    retry_response = await client.post(f"/api/v1/jobs/{job_id}/retry")
    assert retry_response.status_code == 200

    completed = await _wait_for_status(client, job_id, {"completed"})
    assert completed["retry_count"] == 1


@pytest.mark.asyncio
async def test_retry_completed_job_is_rejected(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:0.05"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]
    await _wait_for_status(client, job_id, {"completed"})

    retry_response = await client.post(f"/api/v1/jobs/{job_id}/retry")
    assert retry_response.status_code == 409


@pytest.mark.asyncio
async def test_job_logs_capture_lifecycle_and_output(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:0.05"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]
    await _wait_for_status(client, job_id, {"completed"})

    logs = (await client.get(f"/api/v1/jobs/{job_id}/logs")).json()
    joined = "\n".join(logs["lines"])
    assert "Job started." in joined
    assert "Job finished: completed." in joined
    assert "dummy scan of" in joined

    filtered = (await client.get(f"/api/v1/jobs/{job_id}/logs", params={"search": "started"})).json()
    assert filtered["lines"]
    assert all("started" in line.lower() for line in filtered["lines"])


@pytest.mark.asyncio
async def test_list_jobs_filters_by_assessment_and_status(client: AsyncClient) -> None:
    await _ensure_dummy_tool_row()
    _dummy_plugin_config().arguments = ["duration:0.05"]

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id)
    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": [DUMMY_TOOL_NAME]})
    job_id = response.json()["jobs"][0]["id"]
    await _wait_for_status(client, job_id, {"completed"})

    listed = await client.get("/api/v1/jobs", params={"assessment_id": assessment_id, "status": "completed"})
    assert listed.status_code == 200
    assert any(job["id"] == job_id for job in listed.json())

    none_pending = await client.get("/api/v1/jobs", params={"assessment_id": assessment_id, "status": "pending"})
    assert none_pending.json() == []
