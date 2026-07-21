"""ExecutionPlanner's installation/health gate: a job is never queued for a tool that isn't runnable.

Uses Nuclei as the concrete example (a real, always-registered
detection-only plugin -- see ``backend/plugins/plugins/nuclei`` -- that
has no ``execute()`` implementation and, on most dev/CI machines, no
installed binary either). Before this gate existed, planning a job for an
uninstalled tool produced a ``PENDING`` job that the execution engine would
dequeue, run, and only then fail on -- a real installation problem
surfacing as a late runtime failure instead of an immediate, accurate
planning-time skip. Skipped outright if Nuclei happens to be installed on
the machine running this test, since then there's nothing "not installed"
to prove.
"""

import shutil
import uuid

import pytest
from httpx import AsyncClient

NUCLEI_INSTALLED = shutil.which("nuclei") is not None
pytestmark = pytest.mark.skipif(NUCLEI_INSTALLED, reason="nuclei is installed on this machine")


async def _create_assessment(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/assessments",
        json={"name": f"Nuclei-health-gate-{uuid.uuid4().hex[:8]}", "assessment_type": "web_application", "tags": []},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _add_target(client: AsyncClient, assessment_id: str, target_type: str, value: str) -> str:
    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets", json={"target_type": target_type, "target_value": value}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_execute_against_uninstalled_tool_is_skipped_not_queued(client: AsyncClient) -> None:
    """Planning a job for Nuclei, uninstalled, must SKIP at plan time -- never reach PENDING/RUNNING."""
    await client.post("/api/v1/tools/discover")
    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id, "url", "https://example.com/")

    response = await client.post(f"/api/v1/assessments/{assessment_id}/execute", json={"tool_names": ["nuclei"]})
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["skipped_count"] == 1
    assert body["queued_count"] == 0
    job = body["jobs"][0]
    assert job["status"] == "skipped"
    assert job["status_message"] is not None
    assert "nuclei" in job["status_message"].lower()
    assert "unavailable" in job["status_message"].lower()


async def test_tool_health_endpoint_reports_not_installed_for_nuclei(client: AsyncClient) -> None:
    """The same reason the planner uses is independently visible through Tool Management."""
    await client.post("/api/v1/tools/discover")

    tool_response = await client.get("/api/v1/tools/nuclei")
    assert tool_response.status_code == 200
    tool = tool_response.json()
    assert tool["status"] == "missing"
    assert tool["is_installed"] is False

    health_response = await client.post("/api/v1/tools/nuclei/health")
    assert health_response.status_code == 200
    health = health_response.json()
    assert health["status"] == "error"  # ToolHealthStatus.ERROR -- PluginHealthStatus.NOT_INSTALLED maps to this
    assert health["installed"] is False
    assert health["message"]
