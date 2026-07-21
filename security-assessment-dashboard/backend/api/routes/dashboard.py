"""Intelligence Dashboard API: aggregated, read-only statistics over real collected data."""

import uuid

from fastapi import APIRouter, Query

from backend.api.dependencies.services import DashboardServiceDep
from backend.schemas.dashboard import DashboardRead, StatisticsRead

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardRead, summary="Full intelligence dashboard")
async def get_dashboard(
    service: DashboardServiceDep,
    assessment_id: uuid.UUID | None = Query(default=None, description="Scope to one assessment; omit for the whole workspace."),
) -> DashboardRead:
    return await service.get_dashboard(assessment_id)


@router.get("/statistics", response_model=StatisticsRead, summary="Numbers-only subset of the dashboard")
async def get_statistics(
    service: DashboardServiceDep,
    assessment_id: uuid.UUID | None = Query(default=None),
) -> StatisticsRead:
    return await service.get_statistics(assessment_id)
