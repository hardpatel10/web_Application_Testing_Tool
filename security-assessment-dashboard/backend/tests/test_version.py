"""Tests for the /api/v1/version endpoint."""

import platform

from httpx import AsyncClient

from backend.core.config import get_settings


async def test_version_matches_settings_and_runtime(client: AsyncClient) -> None:
    settings = get_settings()
    response = await client.get(f"{settings.api_prefix}/version")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == settings.app_version
    assert body["python_version"] == platform.python_version()
    assert isinstance(body["build"], str) and body["build"]
