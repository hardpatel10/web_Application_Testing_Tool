"""Tests for the /api/v1/health endpoint."""

from httpx import AsyncClient

from backend.core.config import get_settings


async def test_health_returns_ok_status(client: AsyncClient) -> None:
    settings = get_settings()
    response = await client.get(f"{settings.api_prefix}/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == settings.app_version
    assert body["uptime_seconds"] >= 0
