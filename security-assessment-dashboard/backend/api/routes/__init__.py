"""Versioned API route modules."""

from fastapi import APIRouter

from backend.api.routes import (
    assessments,
    correlation,
    dashboard,
    findings,
    health,
    hosts,
    jobs,
    observations,
    operating_systems,
    plugins,
    scan_profiles,
    search,
    services,
    system,
    targets,
    technologies,
    tools,
    version,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(version.router)
api_router.include_router(system.router)
api_router.include_router(assessments.router)
api_router.include_router(targets.top_level_router)
api_router.include_router(targets.router)
api_router.include_router(plugins.router)
api_router.include_router(tools.router)
api_router.include_router(scan_profiles.router)
api_router.include_router(jobs.router)
api_router.include_router(hosts.router)
api_router.include_router(services.router)
api_router.include_router(technologies.router)
api_router.include_router(observations.router)
api_router.include_router(operating_systems.router)
api_router.include_router(search.router)
api_router.include_router(findings.router)
api_router.include_router(correlation.router)
api_router.include_router(dashboard.router)
