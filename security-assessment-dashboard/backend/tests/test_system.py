"""Tests for the /api/v1/system endpoint."""

import os
import platform

from httpx import AsyncClient

from backend.core.config import get_settings


async def test_system_returns_real_host_information(client: AsyncClient) -> None:
    settings = get_settings()
    response = await client.get(f"{settings.api_prefix}/system")

    assert response.status_code == 200
    body = response.json()
    assert body["operating_system"] == platform.system()
    assert body["hostname"]
    assert body["cpu_count"] == (os.cpu_count() or 0)
    assert body["total_memory_bytes"] > 0
    assert body["available_memory_bytes"] > 0
