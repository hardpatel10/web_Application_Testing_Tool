"""Tests for the Scan Profile management API (``/tools/{tool_name}/profiles``).

Exercises the real HTTP surface end-to-end; the plugin-internal behavior
(command generation, XML parsing, normalization) is covered by
``test_nmap_plugin.py``. Every custom-profile test cleans up after itself
so it never leaks a file into the real ``data/profiles/nmap/`` directory
across test runs.
"""

from httpx import AsyncClient


async def test_list_profiles_returns_every_built_in_profile(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tools/nmap/profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert len(profiles) >= 30
    assert all(profile["built_in"] for profile in profiles)


async def test_list_profiles_filters_by_category_and_risk(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tools/nmap/profiles", params={"category": "ssl_tls"})
    assert response.status_code == 200
    assert response.json() and all(p["category"] == "ssl_tls" for p in response.json())

    response = await client.get("/api/v1/tools/nmap/profiles", params={"risk_level": "high"})
    assert response.status_code == 200
    assert response.json() and all(p["risk_level"] == "high" for p in response.json())

    response = await client.get("/api/v1/tools/nmap/profiles", params={"query": "heartbleed"})
    assert response.status_code == 200
    assert any(p["id"] == "heartbleed" for p in response.json())


async def test_get_one_profile(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tools/nmap/profiles/tcp_full")
    assert response.status_code == 200
    assert response.json()["id"] == "tcp_full"


async def test_get_unknown_profile_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tools/nmap/profiles/does-not-exist")
    assert response.status_code == 404


async def test_profiles_for_a_tool_without_profile_support_is_a_client_error(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tools/nikto/profiles")
    assert response.status_code == 422
    assert "Scan Profiles" in response.json()["error"]["message"]


async def test_preview_command_matches_direct_command_builder_output(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tools/nmap/profiles/preview-command",
        json={"profile_id": "ssl_enum", "target_value": "example.com", "advanced_options": {"timing": 4}},
    )
    assert response.status_code == 200
    command = response.json()["command"]
    assert command[-1] == "example.com"
    assert "-T4" in command
    assert "ssl-enum-ciphers" in command


async def test_preview_command_unknown_profile_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tools/nmap/profiles/preview-command", json={"profile_id": "nope", "target_value": "example.com"}
    )
    assert response.status_code == 404


async def test_custom_profile_full_lifecycle(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/tools/nmap/profiles",
        json={
            "id": "api_test_profile", "name": "API Test Profile", "description": "d", "category": "tcp",
            "supported_targets": ["ipv4"], "arguments": ["-sT"],
        },
    )
    assert create_response.status_code == 201, create_response.text
    assert create_response.json()["built_in"] is False

    try:
        get_response = await client.get("/api/v1/tools/nmap/profiles/api_test_profile")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "API Test Profile"

        update_response = await client.put(
            "/api/v1/tools/nmap/profiles/api_test_profile",
            json={
                "id": "api_test_profile", "name": "Renamed", "description": "d2", "category": "tcp",
                "supported_targets": ["ipv4"], "arguments": ["-sT", "-sV"],
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Renamed"

        export_response = await client.get("/api/v1/tools/nmap/profiles/api_test_profile/export")
        assert export_response.status_code == 200
        assert export_response.json()["id"] == "api_test_profile"

        duplicate_response = await client.post(
            "/api/v1/tools/nmap/profiles/api_test_profile/duplicate", json={"new_id": "api_test_profile_copy"}
        )
        assert duplicate_response.status_code == 201
        assert duplicate_response.json()["id"] == "api_test_profile_copy"

        import_response = await client.post(
            "/api/v1/tools/nmap/profiles/import",
            json={"profile": {**export_response.json(), "id": "api_test_profile_imported"}},
        )
        assert import_response.status_code == 201
        assert import_response.json()["id"] == "api_test_profile_imported"
    finally:
        for profile_id in ("api_test_profile", "api_test_profile_copy", "api_test_profile_imported"):
            await client.delete(f"/api/v1/tools/nmap/profiles/{profile_id}")

    assert (await client.get("/api/v1/tools/nmap/profiles/api_test_profile")).status_code == 404


async def test_create_profile_with_duplicate_id_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tools/nmap/profiles",
        json={"id": "tcp_full", "name": "N", "description": "d", "category": "tcp", "supported_targets": ["ipv4"]},
    )
    assert response.status_code == 422


async def test_built_in_profile_cannot_be_edited_via_api(client: AsyncClient) -> None:
    response = await client.put(
        "/api/v1/tools/nmap/profiles/tcp_full",
        json={"id": "tcp_full", "name": "x", "description": "d", "category": "tcp", "supported_targets": ["ipv4"]},
    )
    assert response.status_code == 422


async def test_built_in_profile_cannot_be_deleted_via_api(client: AsyncClient) -> None:
    response = await client.delete("/api/v1/tools/nmap/profiles/tcp_full")
    assert response.status_code == 422
    # Confirm it's still there.
    assert (await client.get("/api/v1/tools/nmap/profiles/tcp_full")).status_code == 200
