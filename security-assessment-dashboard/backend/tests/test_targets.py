"""Tests for target CRUD, validation, bulk import, and export."""

import uuid

import pytest
from httpx import AsyncClient


async def _create_assessment(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/assessments",
        json={"name": f"Target-tests-{uuid.uuid4().hex[:8]}", "assessment_type": "network", "tags": []},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_target_normalizes_value(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets",
        json={"target_type": "cidr", "target_value": "10.0.0.5/24"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["target_value"] == "10.0.0.0/24"


@pytest.mark.asyncio
async def test_create_invalid_target_returns_422(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets",
        json={"target_type": "ipv4", "target_value": "999.999.999.999"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_create_duplicate_target_returns_409(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)
    payload = {"target_type": "hostname", "target_value": "db01"}

    first = await client.post(f"/api/v1/assessments/{assessment_id}/targets", json=payload)
    assert first.status_code == 201

    second = await client.post(f"/api/v1/assessments/{assessment_id}/targets", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_enable_disable_target(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)
    created = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets", json={"target_type": "domain", "target_value": "example.org"}
    )
    target_id = created.json()["id"]
    assert created.json()["enabled"] is True

    disabled = await client.post(f"/api/v1/assessments/{assessment_id}/targets/{target_id}/disable")
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    enabled = await client.post(f"/api/v1/assessments/{assessment_id}/targets/{target_id}/enable")
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True


@pytest.mark.asyncio
async def test_duplicate_target_hostname_auto_suffix(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)
    created = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets", json={"target_type": "hostname", "target_value": "webserver01"}
    )
    target_id = created.json()["id"]

    duplicate = await client.post(f"/api/v1/assessments/{assessment_id}/targets/{target_id}/duplicate", json={})

    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["target_value"] == "copy-webserver01"


@pytest.mark.asyncio
async def test_duplicate_ip_target_without_value_returns_422(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)
    created = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets", json={"target_type": "ipv4", "target_value": "10.0.0.1"}
    )
    target_id = created.json()["id"]

    duplicate = await client.post(f"/api/v1/assessments/{assessment_id}/targets/{target_id}/duplicate", json={})

    assert duplicate.status_code == 422
    assert "explicit target_value" in duplicate.json()["error"]["message"]


@pytest.mark.asyncio
async def test_bulk_import_txt_summary(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)
    content = b"10.0.0.1\nnot a valid host!!\nexample.com\nexample.com\n"

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets/bulk-import",
        files={"file": ("targets.txt", content, "text/plain")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_lines"] == 4
    assert body["imported"] == 2  # 10.0.0.1 and example.com
    assert body["skipped_duplicates"] == 1  # the second example.com
    assert body["skipped_invalid"] == 1  # "not a valid host!!"


@pytest.mark.asyncio
async def test_bulk_import_csv_with_header_and_duplicates(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)
    await client.post(
        f"/api/v1/assessments/{assessment_id}/targets", json={"target_type": "domain", "target_value": "preexisting.com"}
    )
    content = b"target_type,target_value\nipv4,10.0.0.9\ndomain,preexisting.com\n"

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets/bulk-import",
        files={"file": ("targets.csv", content, "text/csv")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 1  # only 10.0.0.9; header skipped, preexisting.com deduped
    assert body["skipped_duplicates"] == 1


@pytest.mark.asyncio
async def test_export_targets_csv(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)
    await client.post(f"/api/v1/assessments/{assessment_id}/targets", json={"target_type": "url", "target_value": "https://example.com"})

    response = await client.get(f"/api/v1/assessments/{assessment_id}/targets/export", params={"format": "csv"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "https://example.com" in response.text


@pytest.mark.asyncio
async def test_validate_endpoint_reports_invalid(client: AsyncClient) -> None:
    assessment_id = await _create_assessment(client)

    valid = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets/validate", json={"target_type": "url", "target_value": "HTTPS://Example.com"}
    )
    assert valid.status_code == 200
    assert valid.json() == {"valid": True, "normalized_value": "https://example.com", "message": None}

    invalid = await client.post(
        f"/api/v1/assessments/{assessment_id}/targets/validate", json={"target_type": "domain", "target_value": "localhost"}
    )
    assert invalid.status_code == 200
    assert invalid.json()["valid"] is False
