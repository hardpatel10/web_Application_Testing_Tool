"""Dependency providers that construct service-layer instances."""

from typing import Annotated

from fastapi import Depends, Request

from backend.api.dependencies.config import SettingsDep
from backend.api.dependencies.db import DbSessionDep
from backend.api.dependencies.plugins import ExecutionManagerDep, PluginManagerDep
from backend.core.config import PROJECT_ROOT, Settings
from backend.services.assessment_service import AssessmentService
from backend.services.correlation_service import CorrelationService
from backend.services.dashboard_service import DashboardService
from backend.services.execution_service import ExecutionService
from backend.services.finding_query_service import FindingQueryService
from backend.services.health_service import HealthService
from backend.services.host_inventory_query_service import HostInventoryQueryService
from backend.services.pipeline_service import PipelineService
from backend.services.plugin_service import PluginService
from backend.services.scan_profile_service import ScanProfileService
from backend.services.system_info_service import SystemInfoService
from backend.services.target_service import TargetService
from backend.services.tool_service import ToolService
from backend.services.version_service import VersionService


def get_health_service(settings: SettingsDep) -> HealthService:
    return HealthService(settings)


def get_version_service(settings: SettingsDep) -> VersionService:
    return VersionService(settings, PROJECT_ROOT)


def get_system_info_service() -> SystemInfoService:
    return SystemInfoService()


def get_app_start_time(request: Request) -> float:
    """Return the monotonic timestamp recorded at application startup."""
    return request.app.state.start_time


def get_assessment_service(session: DbSessionDep, settings: SettingsDep) -> AssessmentService:
    return AssessmentService(session, settings)


def get_target_service(session: DbSessionDep) -> TargetService:
    return TargetService(session)


def get_plugin_service(manager: PluginManagerDep) -> PluginService:
    return PluginService(manager)


def get_tool_service(session: DbSessionDep, manager: PluginManagerDep) -> ToolService:
    return ToolService(session, manager)


def get_execution_service(
    session: DbSessionDep, plugin_manager: PluginManagerDep, execution_manager: ExecutionManagerDep
) -> ExecutionService:
    return ExecutionService(session, plugin_manager, execution_manager)


def get_scan_profile_service(manager: PluginManagerDep) -> ScanProfileService:
    return ScanProfileService(manager)


def get_pipeline_service(
    session: DbSessionDep, plugin_manager: PluginManagerDep, execution_manager: ExecutionManagerDep
) -> PipelineService:
    return PipelineService(session, plugin_manager, execution_manager)


def get_host_inventory_query_service(session: DbSessionDep) -> HostInventoryQueryService:
    return HostInventoryQueryService(session)


def get_finding_query_service(session: DbSessionDep) -> FindingQueryService:
    return FindingQueryService(session)


def get_correlation_service(session: DbSessionDep) -> CorrelationService:
    return CorrelationService(session)


def get_dashboard_service(session: DbSessionDep) -> DashboardService:
    return DashboardService(session)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
VersionServiceDep = Annotated[VersionService, Depends(get_version_service)]
SystemInfoServiceDep = Annotated[SystemInfoService, Depends(get_system_info_service)]
AppStartTimeDep = Annotated[float, Depends(get_app_start_time)]
AssessmentServiceDep = Annotated[AssessmentService, Depends(get_assessment_service)]
TargetServiceDep = Annotated[TargetService, Depends(get_target_service)]
PluginServiceDep = Annotated[PluginService, Depends(get_plugin_service)]
ToolServiceDep = Annotated[ToolService, Depends(get_tool_service)]
ExecutionServiceDep = Annotated[ExecutionService, Depends(get_execution_service)]
ScanProfileServiceDep = Annotated[ScanProfileService, Depends(get_scan_profile_service)]
PipelineServiceDep = Annotated[PipelineService, Depends(get_pipeline_service)]
HostInventoryQueryServiceDep = Annotated[HostInventoryQueryService, Depends(get_host_inventory_query_service)]
FindingQueryServiceDep = Annotated[FindingQueryService, Depends(get_finding_query_service)]
CorrelationServiceDep = Annotated[CorrelationService, Depends(get_correlation_service)]
DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]
