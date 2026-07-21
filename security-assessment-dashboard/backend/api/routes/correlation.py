"""Correlation Engine control/status API.

``POST /correlation/run`` is the engine's one explicit trigger -- per this
phase's "do not modify the execution engine" constraint, the Correlation
Engine is never invoked as a side effect of a completed job; it is its own,
separately-orchestrated stage the frontend calls explicitly (a "Run
Correlation" action, and automatically after a scan finishes -- see the
Findings/Dashboard pages), never something ``backend.workers`` calls into.
"""

from fastapi import APIRouter

from backend.api.dependencies.services import CorrelationServiceDep, FindingQueryServiceDep
from backend.correlation.registry import get_rule_registry
from backend.schemas.finding import CorrelationRunRequest, CorrelationRunResultRead, CorrelationStatusRead

router = APIRouter(prefix="/correlation", tags=["Correlation"])


@router.post("/run", response_model=CorrelationRunResultRead, summary="Run the Correlation Engine")
async def run_correlation(request: CorrelationRunRequest, service: CorrelationServiceDep) -> CorrelationRunResultRead:
    if request.assessment_id is not None:
        summary = await service.correlate_assessment(request.assessment_id)
    else:
        summary = await service.correlate_all()
    return CorrelationRunResultRead(
        assessment_id=request.assessment_id,
        hosts_evaluated=summary.hosts_evaluated,
        rules_evaluated=summary.rules_evaluated,
        rule_count=len(summary.rule_ids),
        findings_created=summary.findings_created,
        findings_updated=summary.findings_updated,
    )


@router.get("/status", response_model=CorrelationStatusRead, summary="Correlation Engine status and run history")
async def correlation_status(service: FindingQueryServiceDep) -> CorrelationStatusRead:
    return await service.correlation_status(registered_rule_count=len(get_rule_registry()))
