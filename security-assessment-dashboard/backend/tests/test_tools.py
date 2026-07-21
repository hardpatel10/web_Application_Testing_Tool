"""Tests for Tool Management: discovery, configuration, health, validation.

Tools' actual installation state depends on what's installed on the
machine running the tests, so assertions here are host-agnostic — they
check structural invariants (e.g. "not installed implies no version and
no path", i.e. no fabricated data) rather than asserting any specific
tool is or isn't present.
"""

import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient

from backend.services.tool_service import SUPPORTED_TOOL_IDS


async def _discover(client: AsyncClient) -> list[dict]:
    response = await client.post("/api/v1/tools/discover")
    assert response.status_code == 200, response.text
    return response.json()["tools"]


async def test_discover_registers_every_supported_tool(client: AsyncClient) -> None:
    tools = await _discover(client)

    assert {tool["name"] for tool in tools} == set(SUPPORTED_TOOL_IDS)


async def test_discover_never_fabricates_installation_data(client: AsyncClient) -> None:
    """A tool that isn't installed must never report a version or a path."""
    tools = await _discover(client)

    for tool in tools:
        if not tool["is_installed"]:
            assert tool["version"] is None, f"{tool['name']} reports a version while not installed"
            assert tool["status"] in ("missing", "disabled"), tool["status"]


async def test_list_tools_supports_search_and_filter(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.get("/api/v1/tools", params={"search": "map"})
    assert response.status_code == 200
    assert all("map" in tool["name"] or "map" in tool["display_name"].lower() for tool in response.json())

    response = await client.get("/api/v1/tools", params={"status": "missing"})
    assert response.status_code == 200
    assert all(tool["status"] == "missing" for tool in response.json())


async def test_get_tool_detail_includes_plugin_metadata(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.get("/api/v1/tools/nmap")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "nmap"
    assert "ipv4" in body["supported_targets"]
    assert body["license"] == "NPSL"
    assert body["configuration"]["timeout"] is None  # nothing configured yet


async def test_get_tool_detail_surfaces_install_instructions_when_declared(client: AsyncClient) -> None:
    """Nuclei's manifest declares Linux install guidance; the API must pass it through untouched."""
    await _discover(client)

    response = await client.get("/api/v1/tools/nuclei")
    assert response.status_code == 200
    body = response.json()
    assert body["install_instructions"] is not None
    assert "linux" in body["install_instructions"]
    assert "github.com/projectdiscovery/nuclei" in body["install_instructions"]["linux"]


async def test_get_tool_detail_install_instructions_is_none_when_manifest_omits_it(client: AsyncClient) -> None:
    """A plugin manifest with no install_instructions field must not error -- just report None."""
    await _discover(client)

    response = await client.get("/api/v1/tools/dirsearch")
    assert response.status_code == 200
    assert response.json()["install_instructions"] is None


async def test_get_unknown_tool_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tools/not-a-real-tool")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_update_configuration_persists_and_round_trips(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.put(
        "/api/v1/tools/nuclei/configuration",
        json={"timeout": 600, "rate_limit": 50, "retries": 2, "http_proxy": "127.0.0.1:8080", "arguments": ["-silent"]},
    )
    assert response.status_code == 200, response.text
    config = response.json()["configuration"]
    assert config["timeout"] == 600
    assert config["rate_limit"] == 50
    assert config["http_proxy"] == "127.0.0.1:8080"
    assert config["arguments"] == ["-silent"]

    # Re-fetch to confirm it was actually persisted, not just echoed back.
    response = await client.get("/api/v1/tools/nuclei")
    assert response.json()["configuration"]["timeout"] == 600


async def test_update_configuration_rejects_nonexistent_wordlist(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.put(
        "/api/v1/tools/gobuster/configuration",
        json={"wordlists": {"directory": "C:/definitely/does/not/exist.txt"}},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"


async def test_update_configuration_accepts_real_wordlist_file(client: AsyncClient) -> None:
    await _discover(client)

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as handle:
        handle.write(b"admin\nlogin\n")
        wordlist_path = handle.name

    try:
        response = await client.put(
            "/api/v1/tools/ffuf/configuration", json={"wordlists": {"fuzzing": wordlist_path}}
        )
        assert response.status_code == 200, response.text
        assert response.json()["configuration"]["wordlists"]["fuzzing"] == wordlist_path
    finally:
        Path(wordlist_path).unlink(missing_ok=True)


async def test_update_configuration_rejects_wrong_custom_executable(client: AsyncClient) -> None:
    await _discover(client)

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as handle:
        handle.write(b"not a real binary")
        wrong_path = handle.name

    try:
        response = await client.put("/api/v1/tools/nmap/configuration", json={"custom_executable_path": wrong_path})
        assert response.status_code == 422
    finally:
        Path(wrong_path).unlink(missing_ok=True)


async def test_disable_tool_via_configuration(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.put("/api/v1/tools/subfinder/configuration", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["status"] == "disabled"
    assert response.json()["enabled"] is False


async def test_health_check_is_live_not_cached(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.post("/api/v1/tools/nmap/health")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "nmap"
    assert body["status"] in ("healthy", "warning", "error")
    assert body["checked_at"] is not None


async def test_validate_single_tool(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.post("/api/v1/tools/validate", json={"name": "amass"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["name"] == "amass"


async def test_validate_all_tools_when_no_name_given(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.post("/api/v1/tools/validate", json={})
    assert response.status_code == 200
    assert {result["name"] for result in response.json()} == set(SUPPORTED_TOOL_IDS)


async def test_browse_filesystem_lists_a_real_directory(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tools/browse-filesystem", params={"path": str(Path.home())})
    assert response.status_code == 200
    body = response.json()
    assert body["path"] == str(Path.home())
    assert isinstance(body["entries"], list)


async def test_browse_filesystem_rejects_nonexistent_path(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tools/browse-filesystem", params={"path": "Z:/this/path/does/not/exist"})
    assert response.status_code == 422
