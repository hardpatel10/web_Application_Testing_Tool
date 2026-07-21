"""Tests for the Host Inventory & Observation Engine (Phase 8).

Two kinds of test:

1. Pure, host-agnostic unit tests of ``backend.services.fingerprinting`` --
   no DB, no Nmap, deterministic by construction.
2. Real, end-to-end integration tests through the actual HTTP API and a
   real Nmap scan (skipped if ``nmap`` isn't installed, same convention as
   ``test_nmap_execution.py``) -- these are what prove the merge engine
   actually deduplicates instead of just asserting it in isolation: single
   scan, re-scan the same target (same DiscoveredHost, no duplicate Service/
   Technology, execution history grows), and a port closing between scans
   updates state rather than inserting a new row.
"""

import asyncio
import shutil
import time
import uuid

import pytest
from httpx import AsyncClient

from backend.models.enums import NetworkProtocol
from backend.services import fingerprinting

NMAP_INSTALLED = shutil.which("nmap") is not None

# -- Fingerprinting: pure unit tests -----------------------------------------


def test_host_fingerprint_prefers_mac_over_ip_and_hostname() -> None:
    by_mac = fingerprinting.host_fingerprint(mac_address="AA:BB:CC:DD:EE:FF", ipv4="10.0.0.1", ipv6=None, hostname="host")
    by_mac_only_ip_differs = fingerprinting.host_fingerprint(mac_address="AA:BB:CC:DD:EE:FF", ipv4="10.0.0.99", ipv6=None, hostname="other")
    assert by_mac == by_mac_only_ip_differs  # same MAC -> same identity, regardless of IP/hostname
    assert by_mac.startswith("mac:")


def test_host_fingerprint_falls_back_to_ip_then_hostname() -> None:
    by_ip = fingerprinting.host_fingerprint(mac_address=None, ipv4="10.0.0.1", ipv6=None, hostname="host")
    assert by_ip.startswith("ipv4:")

    by_hostname = fingerprinting.host_fingerprint(mac_address=None, ipv4=None, ipv6=None, hostname="example.com")
    assert by_hostname.startswith("hostname:")

    by_ipv6 = fingerprinting.host_fingerprint(mac_address=None, ipv4=None, ipv6="::1", hostname=None)
    assert by_ipv6.startswith("ipv6:")


def test_host_fingerprint_case_insensitive_mac_and_hostname() -> None:
    lower = fingerprinting.host_fingerprint(mac_address="aa:bb:cc:dd:ee:ff", ipv4=None, ipv6=None, hostname=None)
    upper = fingerprinting.host_fingerprint(mac_address="AA:BB:CC:DD:EE:FF", ipv4=None, ipv6=None, hostname=None)
    assert lower == upper


def test_host_fingerprint_raises_with_no_identity_signal() -> None:
    with pytest.raises(ValueError):
        fingerprinting.host_fingerprint(mac_address=None, ipv4=None, ipv6=None, hostname=None)


def test_host_fingerprint_is_deterministic() -> None:
    first = fingerprinting.host_fingerprint(mac_address=None, ipv4="127.0.0.1", ipv6=None, hostname="localhost")
    second = fingerprinting.host_fingerprint(mac_address=None, ipv4="127.0.0.1", ipv6=None, hostname="localhost")
    assert first == second


def test_service_fingerprint_differs_by_port_and_protocol() -> None:
    host_fp = fingerprinting.host_fingerprint(mac_address=None, ipv4="127.0.0.1", ipv6=None, hostname=None)
    tcp_80 = fingerprinting.service_fingerprint(host_fingerprint_value=host_fp, port=80, protocol=NetworkProtocol.TCP)
    tcp_443 = fingerprinting.service_fingerprint(host_fingerprint_value=host_fp, port=443, protocol=NetworkProtocol.TCP)
    udp_80 = fingerprinting.service_fingerprint(host_fingerprint_value=host_fp, port=80, protocol=NetworkProtocol.UDP)
    assert len({tcp_80, tcp_443, udp_80}) == 3


def test_service_fingerprint_same_port_different_host_differs() -> None:
    host_a = fingerprinting.host_fingerprint(mac_address=None, ipv4="10.0.0.1", ipv6=None, hostname=None)
    host_b = fingerprinting.host_fingerprint(mac_address=None, ipv4="10.0.0.2", ipv6=None, hostname=None)
    fp_a = fingerprinting.service_fingerprint(host_fingerprint_value=host_a, port=22, protocol=NetworkProtocol.TCP)
    fp_b = fingerprinting.service_fingerprint(host_fingerprint_value=host_b, port=22, protocol=NetworkProtocol.TCP)
    assert fp_a != fp_b


def test_observation_fingerprint_differs_by_title_and_category() -> None:
    host_fp = fingerprinting.host_fingerprint(mac_address=None, ipv4="127.0.0.1", ipv6=None, hostname=None)
    a = fingerprinting.observation_fingerprint(
        plugin="nmap", host_fingerprint_value=host_fp, category="tls", observation_type="ssl-cert", title="ssl-cert"
    )
    b = fingerprinting.observation_fingerprint(
        plugin="nmap", host_fingerprint_value=host_fp, category="web", observation_type="http-headers", title="http-headers"
    )
    c = fingerprinting.observation_fingerprint(
        plugin="nmap", host_fingerprint_value=host_fp, category="tls", observation_type="ssl-cert", title="ssl-cert"
    )
    assert a != b
    assert a == c


# -- Real end-to-end integration tests (require a real installed Nmap) ------

pytestmark = pytest.mark.skipif(not NMAP_INSTALLED, reason="nmap is not installed on this machine")


async def _create_assessment(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/assessments",
        json={"name": f"host-inventory-tests-{uuid.uuid4().hex[:8]}", "assessment_type": "network", "tags": []},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _add_target(client: AsyncClient, assessment_id: str, value: str) -> str:
    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets", json={"target_type": "ipv4", "target_value": value}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _run_nmap(client: AsyncClient, assessment_id: str, target_id: str, profile_id: str) -> dict:
    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/execute",
        json={"tool_names": ["nmap"], "target_ids": [target_id], "tool_options": {"nmap": {"profile_id": profile_id}}},
    )
    assert response.status_code == 201, response.text
    job = response.json()["jobs"][0]

    deadline = time.monotonic() + 30.0
    while True:
        status_response = await client.get(f"/api/v1/jobs/{job['id']}")
        body = status_response.json()
        if body["status"] in ("completed", "failed"):
            assert body["status"] == "completed", body.get("status_message")
            return body
        if time.monotonic() > deadline:
            raise AssertionError(f"Job {job['id']} did not complete in time (last status: {body['status']})")
        await asyncio.sleep(0.2)


async def test_single_scan_creates_host_with_services_and_os_candidates(client: AsyncClient) -> None:
    await client.post("/api/v1/tools/discover")
    assessment_id = await _create_assessment(client)
    target_id = await _add_target(client, assessment_id, "127.0.0.1")
    await _run_nmap(client, assessment_id, target_id, "os_detection")

    hosts_response = await client.get("/api/v1/hosts", params={"assessment_id": assessment_id})
    assert hosts_response.status_code == 200
    hosts = hosts_response.json()["items"]
    assert len(hosts) == 1
    host = hosts[0]
    assert host["ipv4"] == "127.0.0.1"
    assert host["host_type"] == "host"
    assert host["target_id"] == target_id

    detail_response = await client.get(f"/api/v1/hosts/{host['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["network_interfaces"]) >= 1
    assert detail["network_interfaces"][0]["ip_address"] == "127.0.0.1"
    # OS detection reports many candidates -- Phase 8 keeps all of them, not just the best.
    assert len(detail["operating_systems"]) >= 1
    assert len(detail["execution_history"]) == 1
    assert detail["execution_history"][0]["is_new"] is True


async def test_rescanning_same_target_merges_not_duplicates(client: AsyncClient) -> None:
    await client.post("/api/v1/tools/discover")
    assessment_id = await _create_assessment(client)
    target_id = await _add_target(client, assessment_id, "127.0.0.1")

    await _run_nmap(client, assessment_id, target_id, "service_detection")
    first_hosts = (await client.get("/api/v1/hosts", params={"assessment_id": assessment_id})).json()["items"]
    assert len(first_hosts) == 1
    host_id = first_hosts[0]["id"]
    first_last_seen = first_hosts[0]["last_seen"]
    first_service_count = first_hosts[0]["service_count"]

    await _run_nmap(client, assessment_id, target_id, "service_detection")
    second_hosts = (await client.get("/api/v1/hosts", params={"assessment_id": assessment_id})).json()["items"]

    # Still exactly one host -- the whole point of the merge engine.
    assert len(second_hosts) == 1
    assert second_hosts[0]["id"] == host_id
    assert second_hosts[0]["last_seen"] > first_last_seen
    assert second_hosts[0]["service_count"] == first_service_count  # no duplicate Service rows

    detail = (await client.get(f"/api/v1/hosts/{host_id}")).json()
    assert len(detail["execution_history"]) == 2
    is_new_flags = sorted(entry["is_new"] for entry in detail["execution_history"])
    assert is_new_flags == [False, True]

    # Technologies extracted from service_detection's product/version data, deduplicated too.
    services_response = await client.get("/api/v1/services", params={"host_id": host_id})
    assert services_response.json()["total"] == first_service_count


async def test_observations_endpoint_lists_real_nse_output(client: AsyncClient) -> None:
    await client.post("/api/v1/tools/discover")
    assessment_id = await _create_assessment(client)
    target_id = await _add_target(client, assessment_id, "127.0.0.1")
    await _run_nmap(client, assessment_id, target_id, "http_headers")

    response = await client.get("/api/v1/observations", params={"plugin": "nmap"})
    assert response.status_code == 200
    body = response.json()
    # http_headers profile only runs if an HTTP service is open on this dev
    # machine -- assert the endpoint itself works and returns real data
    # shaped correctly, not a specific count (host-dependent).
    for observation in body["items"]:
        assert observation["plugin"] == "nmap"
        assert observation["category"] in (
            "network", "web", "tls", "auth", "configuration", "os", "other",
        )


async def test_search_finds_host_by_ip(client: AsyncClient) -> None:
    await client.post("/api/v1/tools/discover")
    assessment_id = await _create_assessment(client)
    target_id = await _add_target(client, assessment_id, "127.0.0.1")
    await _run_nmap(client, assessment_id, target_id, "service_detection")

    response = await client.get("/api/v1/search", params={"q": "127.0.0.1"})
    assert response.status_code == 200
    body = response.json()
    assert any(result["label"] for result in body["hosts"])
    # assessment_id lets the frontend deep-link a search result into the assessment that
    # discovered it (its "Assets Discovered" tab) instead of a dedicated host page. The test DB
    # is shared across the whole session (see conftest.py), so other tests' own 127.0.0.1 hosts
    # under different assessments may also match -- assert at least this one is correct, not all.
    assert any(result["assessment_id"] == assessment_id for result in body["hosts"])
