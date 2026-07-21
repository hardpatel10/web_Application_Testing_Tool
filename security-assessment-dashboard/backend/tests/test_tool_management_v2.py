"""Tests for Phase 10 (Tool Management 2.0): diagnostics, per-tool refresh/validate,
overall status, tolerant version detection, and Scan Profile enable/disable.

Like ``test_tools.py``, assertions here are host-agnostic where a tool's
installed state matters (never assert a specific tool IS installed), but
several checks (diagnostics shape, disable/enable round-trip on nmap's
built-in profiles) don't depend on any tool actually being present.
"""

from httpx import AsyncClient

from backend.plugins.sdk.detection_helpers import is_version_at_least, parse_version_tuple


async def _discover(client: AsyncClient) -> None:
    response = await client.post("/api/v1/tools/discover")
    assert response.status_code == 200, response.text


# -- Pure version-comparison helpers (no subprocess, no installed-tool dependency) -----------


def test_parse_version_tuple_ignores_prerelease_suffix() -> None:
    assert parse_version_tuple("2.5.0-beta") == (2, 5, 0)
    assert parse_version_tuple("7.94") == (7, 94)
    assert parse_version_tuple("not-a-version") == ()


def test_is_version_at_least_compares_numerically_not_lexically() -> None:
    # Lexical comparison would get "7.9" > "7.10" backwards; numeric must not.
    assert is_version_at_least("7.10", "7.9")
    assert is_version_at_least("7.80", "7.80")
    assert not is_version_at_least("6.49", "7.00")


# -- Diagnostics --------------------------------------------------------------------------


async def test_diagnostics_endpoint_reports_structural_fields(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.get("/api/v1/tools/nmap/diagnostics")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["name"] == "nmap"
    assert "nmap" in body["binary_names"]
    assert body["detection_method"] in ("path", "search_directory", "custom_path", "not_found")
    assert isinstance(body["path_directories"], list) and body["path_directories"]
    assert isinstance(body["environment_variables"], dict)
    assert isinstance(body["validation_errors"], list)
    assert isinstance(body["validation_warnings"], list)


async def test_diagnostics_never_fabricates_version_when_not_resolved(client: AsyncClient) -> None:
    """No resolved path must always mean no version/command -- never a guessed fallback."""
    await _discover(client)

    response = await client.get("/api/v1/tools/nmap/diagnostics")
    body = response.json()
    if body["resolved_path"] is None:
        assert body["detection_method"] == "not_found"
        assert body["detected_version"] is None
        assert body["version_command"] is None
        assert body["raw_version_output"] is None


async def test_diagnostics_unknown_tool_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tools/not-a-real-tool/diagnostics")
    assert response.status_code == 404


# -- Per-tool refresh / validate ------------------------------------------------------------


async def test_refresh_tool_returns_detail_and_sets_detection_method(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.post("/api/v1/tools/nmap/refresh")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "nmap"
    assert body["detection_method"] in ("path", "search_directory", "custom_path", "not_found")


async def test_refresh_unknown_tool_returns_404(client: AsyncClient) -> None:
    response = await client.post("/api/v1/tools/not-a-real-tool/refresh")
    assert response.status_code == 404


async def test_per_tool_validate_persists_last_validated_at(client: AsyncClient) -> None:
    # The test DB is shared across the whole session (see conftest.py), so another test may
    # have already validated this tool -- assert the timestamp *advances*, not that it starts None.
    await _discover(client)

    before = (await client.get("/api/v1/tools/nmap")).json()["last_validated_at"]

    validate_response = await client.post("/api/v1/tools/nmap/validate")
    assert validate_response.status_code == 200, validate_response.text
    assert validate_response.json()["name"] == "nmap"

    after = (await client.get("/api/v1/tools/nmap")).json()["last_validated_at"]
    assert after is not None
    assert after != before


async def test_getting_tool_detail_does_not_itself_advance_last_validated_at(client: AsyncClient) -> None:
    """Viewing a tool's detail page computes validation for display but must not stamp it as 'validated'."""
    await _discover(client)

    first = (await client.get("/api/v1/tools/nuclei")).json()["last_validated_at"]
    second = (await client.get("/api/v1/tools/nuclei")).json()["last_validated_at"]
    assert first == second


async def test_validate_unknown_tool_reports_invalid_not_a_hard_error(client: AsyncClient) -> None:
    """Matches validate_tools()'s existing bulk contract: an unknown name is reported, not raised,
    so a batch validate request never fails outright over one bad name."""
    response = await client.post("/api/v1/tools/not-a-real-tool/validate")
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["errors"]


# -- Overall status ----------------------------------------------------------------------


async def test_overall_status_is_disabled_when_tool_disabled(client: AsyncClient) -> None:
    await _discover(client)

    disable = await client.put("/api/v1/tools/nikto/configuration", json={"enabled": False})
    assert disable.status_code == 200, disable.text
    assert disable.json()["overall_status"] == "disabled"

    summary = await client.get("/api/v1/tools", params={"search": "nikto"})
    matching = [tool for tool in summary.json() if tool["name"] == "nikto"]
    assert matching and matching[0]["overall_status"] == "disabled"

    # Restore, so this test doesn't leak state into other tests sharing the same DB session.
    await client.put("/api/v1/tools/nikto/configuration", json={"enabled": True})


async def test_overall_status_is_missing_when_tool_not_installed(client: AsyncClient) -> None:
    await _discover(client)

    response = await client.get("/api/v1/tools/nikto")
    body = response.json()
    if not body["is_installed"]:
        assert body["overall_status"] == "missing"


# -- Scan Profile enable/disable ------------------------------------------------------------


async def test_disable_then_enable_a_built_in_profile_round_trips(client: AsyncClient) -> None:
    await _discover(client)

    disable = await client.post("/api/v1/tools/nmap/profiles/tcp_full/disable")
    assert disable.status_code == 200, disable.text
    assert disable.json()["enabled"] is False
    assert disable.json()["built_in"] is True  # disabling never edits/deletes the profile itself

    still_listed = await client.get("/api/v1/tools/nmap/profiles")
    ids = {p["id"] for p in still_listed.json()}
    assert "tcp_full" in ids  # still exists, just disabled

    enable = await client.post("/api/v1/tools/nmap/profiles/tcp_full/enable")
    assert enable.status_code == 200, enable.text
    assert enable.json()["enabled"] is True


async def test_disabling_a_profile_for_a_tool_without_profile_support_is_a_client_error(client: AsyncClient) -> None:
    response = await client.post("/api/v1/tools/whatweb/profiles/anything/disable")
    assert response.status_code == 422


async def test_disabling_an_unknown_profile_returns_404(client: AsyncClient) -> None:
    response = await client.post("/api/v1/tools/nmap/profiles/does-not-exist/disable")
    assert response.status_code == 404
