"""Tests for global search (`GET /search`), independent of any real scanner.

Seeds a host/service/technology/observation/finding directly via a real DB
session (the shape `HostInventoryService`/`CorrelationService` would have
produced), so this runs identically whether or not any tool is installed
on the machine running the tests -- unlike `test_host_inventory.py`'s
Nmap-dependent search test, which only exercises the host-result path.
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.database.session import background_session
from backend.models.assessment import Assessment
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import (
    AssessmentType,
    FindingConfidence,
    FindingSeverity,
    HostState,
    HostType,
    NetworkProtocol,
    ObservationCategory,
    PortState,
    TargetType,
    TechnologyCategory,
)
from backend.models.finding import Finding
from backend.models.observation import Observation
from backend.models.service import Service
from backend.models.target import Target
from backend.models.technology import Technology
from backend.services import fingerprinting


async def _seed_searchable_assessment() -> tuple[uuid.UUID, uuid.UUID]:
    async with background_session() as session:
        assessment = Assessment(name=f"search-{uuid.uuid4()}", assessment_type=AssessmentType.NETWORK)
        session.add(assessment)
        await session.flush()

        target = Target(assessment_id=assessment.id, target_type=TargetType.IPV4, target_value="10.20.30.40")
        session.add(target)
        await session.flush()

        now = datetime.now(timezone.utc)
        host_fp = fingerprinting.host_fingerprint(mac_address=None, ipv4="10.20.30.40", ipv6=None, hostname="searchable-host")
        host = DiscoveredHost(
            target_id=target.id, assessment_id=assessment.id, hostname="searchable-host", ipv4="10.20.30.40",
            host_type=HostType.HOST, state=HostState.UP, fingerprint=host_fp, first_seen=now, last_seen=now,
        )
        session.add(host)
        await session.flush()

        service_fp = fingerprinting.service_fingerprint(host_fingerprint_value=host_fp, port=8080, protocol=NetworkProtocol.TCP)
        session.add(Service(
            host_id=host.id, port=8080, protocol=NetworkProtocol.TCP, state=PortState.OPEN,
            service_name="searchable-service", product="SearchableProduct",
            fingerprint=service_fp, first_seen=now, last_seen=now,
        ))
        session.add(Technology(
            host_id=host.id, name="SearchableTechnology", version="1.0", category=TechnologyCategory.OTHER,
            first_seen=now, last_seen=now,
        ))
        session.add(Observation(
            host_id=host.id, plugin="test", source="test", category=ObservationCategory.OTHER,
            title="SearchableObservation", detail="detail text",
            fingerprint=f"observation:{uuid.uuid4()}", first_seen=now, last_seen=now,
        ))
        session.add(Finding(
            assessment_id=assessment.id, host_id=host.id, rule_id="TEST-001", plugin="test",
            title="SearchableFinding", description="d", impact="i", severity=FindingSeverity.LOW,
            confidence=FindingConfidence.LOW, category="general", remediation="r",
            fingerprint=f"finding:{uuid.uuid4()}", first_seen=now, last_seen=now,
        ))
        await session.flush()
        return assessment.id, host.id


@pytest.mark.asyncio
async def test_search_results_carry_assessment_id_for_every_result_kind(client: AsyncClient) -> None:
    """Every result kind must expose assessment_id so the frontend can deep-link into the
    assessment that discovered it (its Assets Discovered tab) instead of a dedicated page."""
    assessment_id, host_id = await _seed_searchable_assessment()

    response = await client.get("/api/v1/search", params={"q": "searchable"})
    assert response.status_code == 200
    body = response.json()

    for kind in ("hosts", "services", "technologies", "observations"):
        results = body[kind]
        assert len(results) >= 1, f"expected at least one {kind} result"
        for result in results:
            assert result["assessment_id"] == str(assessment_id)
            assert result["host_id"] == str(host_id)

    assert len(body["findings"]) >= 1
    assert body["findings"][0]["assessment_id"] == str(assessment_id)
