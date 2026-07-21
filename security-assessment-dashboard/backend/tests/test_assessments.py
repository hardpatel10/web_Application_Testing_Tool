"""Tests for assessment CRUD, archive/restore, duplicate, and history."""

import uuid

import pytest
from httpx import AsyncClient


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _create_assessment(client: AsyncClient, **overrides: object) -> dict:
    payload = {
        "name": _unique_name("Assessment"),
        "description": "Created by tests.",
        "assessment_type": "web_application",
        "tags": ["Prod", "prod", " staging "],
        **overrides,
    }
    response = await client.post("/api/v1/assessments", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_create_assessment_returns_expected_fields(client: AsyncClient) -> None:
    body = await _create_assessment(client)

    assert body["status"] == "draft"
    assert body["target_count"] == 0
    assert body["tags"] == ["prod", "staging"]  # trimmed, lowercased, de-duplicated


@pytest.mark.asyncio
async def test_create_duplicate_name_returns_409(client: AsyncClient) -> None:
    name = _unique_name("Dup")
    await _create_assessment(client, name=name)

    response = await client.post(
        "/api/v1/assessments",
        json={"name": name, "assessment_type": "network", "tags": []},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_list_assessments_supports_search_and_pagination(client: AsyncClient) -> None:
    unique_token = uuid.uuid4().hex[:10]
    await _create_assessment(client, name=f"Findable-{unique_token}")

    response = await client.get("/api/v1/assessments", params={"search": unique_token, "page": 1, "page_size": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == f"Findable-{unique_token}"


@pytest.mark.asyncio
async def test_update_assessment_changes_fields_and_rejects_direct_archived_status(client: AsyncClient) -> None:
    created = await _create_assessment(client)
    assessment_id = created["id"]

    response = await client.put(f"/api/v1/assessments/{assessment_id}", json={"status": "ready", "description": "Updated."})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["description"] == "Updated."

    rejected = await client.put(f"/api/v1/assessments/{assessment_id}", json={"status": "archived"})
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_archive_then_restore_roundtrip(client: AsyncClient) -> None:
    created = await _create_assessment(client)
    assessment_id = created["id"]
    await client.put(f"/api/v1/assessments/{assessment_id}", json={"status": "ready"})

    archived = await client.post(f"/api/v1/assessments/{assessment_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    already_archived = await client.post(f"/api/v1/assessments/{assessment_id}/archive")
    assert already_archived.status_code == 409

    restored = await client.post(f"/api/v1/assessments/{assessment_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["status"] == "ready"  # restored to its pre-archive status


@pytest.mark.asyncio
async def test_duplicate_assessment_clones_tags_and_targets(client: AsyncClient) -> None:
    source = await _create_assessment(client)
    source_id = source["id"]

    target_response = await client.post(
        f"/api/v1/assessments/{source_id}/targets",
        json={"target_type": "domain", "target_value": "example.com"},
    )
    assert target_response.status_code == 201, target_response.text

    duplicate = await client.post(f"/api/v1/assessments/{source_id}/duplicate", json={})
    assert duplicate.status_code == 201, duplicate.text
    body = duplicate.json()
    assert body["id"] != source_id
    assert body["status"] == "draft"
    assert body["tags"] == ["prod", "staging"]
    assert body["target_count"] == 1


@pytest.mark.asyncio
async def test_delete_assessment_soft_deletes_and_hides_from_list(client: AsyncClient) -> None:
    created = await _create_assessment(client)
    assessment_id = created["id"]

    delete_response = await client.delete(f"/api/v1/assessments/{assessment_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/assessments/{assessment_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_assessment_history_returns_entries(client: AsyncClient) -> None:
    created = await _create_assessment(client)
    assessment_id = created["id"]
    await client.post(f"/api/v1/assessments/{assessment_id}/archive")

    response = await client.get(f"/api/v1/assessments/{assessment_id}/history")
    assert response.status_code == 200
    events = [entry["event_type"] for entry in response.json()["items"]]

    assert "created" in events
    assert "archived" in events
