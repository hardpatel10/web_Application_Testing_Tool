"""Integration tests: Nmap through the real Assessment Execution Engine.

Unlike ``test_nmap_plugin.py`` (pure, host-agnostic unit tests), these
exercise a real scan via ``POST /assessments/{id}/execute`` end-to-end --
planning, queuing, dispatch, real ``execute()``, parsing, normalization,
and DB persistence. Skipped outright if ``nmap`` isn't actually installed
on the machine running the tests, the same host-agnostic philosophy
``test_tools.py``/``test_nmap_plugin.py`` already use. Real network access
is required for the ``scanme.nmap.org`` test specifically; it is skipped
(not failed) if that lookup doesn't succeed.
"""

import asyncio
import shutil
import socket
import time
import uuid

import pytest
from httpx import AsyncClient

NMAP_INSTALLED = shutil.which("nmap") is not None
pytestmark = pytest.mark.skipif(not NMAP_INSTALLED, reason="nmap is not installed on this machine")


def _scanme_reachable() -> bool:
    try:
        socket.getaddrinfo("scanme.nmap.org", 80)
        return True
    except OSError:
        return False


async def _create_assessment(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/assessments",
        json={"name": f"Nmap-execution-tests-{uuid.uuid4().hex[:8]}", "assessment_type": "network", "tags": []},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _add_target(client: AsyncClient, assessment_id: str, target_type: str, value: str) -> str:
    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets", json={"target_type": target_type, "target_value": value}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _wait_for_status(client: AsyncClient, job_id: str, expected: set[str], *, timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        response = await client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in expected:
            return body
        if time.monotonic() > deadline:
            raise AssertionError(f"Job {job_id} did not reach {expected} within {timeout}s (last: {body['status']})")
        await asyncio.sleep(0.2)


async def test_execute_nmap_with_profile_against_localhost(client: AsyncClient) -> None:
    discover = await client.post("/api/v1/tools/discover")
    assert discover.status_code == 200

    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id, "ipv4", "127.0.0.1")

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/execute",
        json={"tool_names": ["nmap"], "tool_options": {"nmap": {"profile_id": "service_detection"}}},
    )
    assert response.status_code == 201, response.text
    job = response.json()["jobs"][0]
    assert job["profile_id"] == "service_detection"

    finished = await _wait_for_status(client, job["id"], {"completed", "failed"})
    assert finished["status"] == "completed", finished.get("status_message")
    assert finished["generated_command"] is not None
    assert "nmap" in finished["generated_command"][0].lower()

    results = await client.get(f"/api/v1/jobs/{job['id']}/results")
    assert results.status_code == 200
    body = results.json()
    assert len(body["hosts"]) == 1
    assert body["hosts"][0]["ip_address"] == "127.0.0.1"

    raw = await client.get(f"/api/v1/jobs/{job['id']}/raw-output")
    assert raw.status_code == 200
    assert raw.json()["format"] == "xml"
    assert "<nmaprun" in raw.json()["content"]


async def test_execute_nmap_with_unknown_profile_is_rejected(client: AsyncClient) -> None:
    await client.post("/api/v1/tools/discover")
    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id, "ipv4", "127.0.0.1")

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/execute",
        json={"tool_names": ["nmap"], "tool_options": {"nmap": {"profile_id": "not-a-real-profile"}}},
    )
    assert response.status_code == 404


async def test_execute_naming_profile_for_tool_without_profile_support_is_rejected(client: AsyncClient) -> None:
    await client.post("/api/v1/tools/discover")
    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id, "ipv4", "127.0.0.1")

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/execute",
        json={"tool_names": ["whatweb"], "tool_options": {"whatweb": {"profile_id": "anything"}}},
    )
    assert response.status_code == 422


@pytest.mark.skipif(not _scanme_reachable(), reason="scanme.nmap.org is not reachable from this environment")
async def test_execute_nmap_against_url_target_is_reduced_to_bare_host_and_runs(client: AsyncClient) -> None:
    """A URL target is not skipped: it is normalized to its bare host before the command is built and run."""
    await client.post("/api/v1/tools/discover")
    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id, "url", "http://scanme.nmap.org/some/path")

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/execute",
        json={"tool_names": ["nmap"], "tool_options": {"nmap": {"profile_id": "http_headers", "advanced_options": {"port_range": "80"}}}},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["skipped_count"] == 0
    job = body["jobs"][0]
    assert job["status"] != "skipped"

    finished = await _wait_for_status(client, job["id"], {"completed", "failed", "timeout"}, timeout=60.0)
    assert finished["generated_command"] is not None
    assert finished["generated_command"][-1] == "scanme.nmap.org"  # scheme/path stripped, bare host only
    assert finished["status"] in ("completed", "failed", "timeout")


@pytest.mark.skipif(not _scanme_reachable(), reason="scanme.nmap.org is not reachable from this environment")
async def test_execute_nmap_against_scanme_nmap_org(client: AsyncClient) -> None:
    """scanme.nmap.org is Nmap's own project-sanctioned public test target -- a lightweight profile only."""
    await client.post("/api/v1/tools/discover")
    assessment_id = await _create_assessment(client)
    await _add_target(client, assessment_id, "hostname", "scanme.nmap.org")

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/execute",
        json={"tool_names": ["nmap"], "tool_options": {"nmap": {"profile_id": "http_headers", "advanced_options": {"port_range": "80"}}}},
    )
    assert response.status_code == 201, response.text
    job = response.json()["jobs"][0]

    finished = await _wait_for_status(client, job["id"], {"completed", "failed", "timeout"}, timeout=60.0)
    # Only assert the job actually ran to a terminal state -- scanme.nmap.org's
    # real availability/firewall behavior is outside this test's control.
    assert finished["status"] in ("completed", "failed", "timeout")
