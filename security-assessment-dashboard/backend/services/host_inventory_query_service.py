"""Read-side service for the Host Inventory & Observation Engine.

Distinct from :class:`backend.services.host_inventory_service.HostInventoryService`
(the write-side merge/upsert engine, only ever called by the execution
worker) — this is the query layer backing the ``/hosts``, ``/services``,
``/technologies``, ``/observations``, ``/operating-systems``, and
``/search`` API routes. Every resource here is read-only from the API's
perspective; rows only ever get written as a side effect of a completed scan.

Follows :class:`backend.services.target_service.TargetService`'s established
search/filter/sort/paginate convention (``Sort``/``Pagination``/``Page``
value objects, a sort-field whitelist set, ``InvalidInputError`` on a bad
field) — consolidated into one service class rather than five (one per
resource) since they're all tightly related facets of the same inventory
and several queries need to join across them anyway.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import InvalidInputError, NotFoundError
from backend.database.pagination import Page, Pagination, Sort, SortDirection
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import HostState, HostType, NetworkProtocol, ObservationCategory, PortState, TechnologyCategory
from backend.models.execution_host import ExecutionHost
from backend.models.finding import Finding
from backend.models.observation import Observation
from backend.models.operating_system import OperatingSystem
from backend.models.service import Service
from backend.models.target import Target
from backend.models.technology import Technology
from backend.models.tool import Tool
from backend.models.tool_execution import ToolExecution
from backend.schemas.host_inventory import (
    ExecutionHistoryEntryRead,
    HostDetailRead,
    HostSummaryRead,
    ObservationRead,
    OperatingSystemRead,
    SearchResponse,
    SearchResult,
    ServiceRead,
    TechnologyRead,
)
from backend.services.query_scoping import host_owned_by_active_assessment, owned_by_active_assessment

_HOST_SORT_FIELDS = {"hostname", "ipv4", "ipv6", "first_seen", "last_seen", "created_at"}
_SERVICE_SORT_FIELDS = {"port", "protocol", "state", "first_seen", "last_seen"}
_TECHNOLOGY_SORT_FIELDS = {"name", "category", "first_seen", "last_seen"}
_OBSERVATION_SORT_FIELDS = {"title", "category", "first_seen", "last_seen"}
_OS_SORT_FIELDS = {"name", "accuracy", "first_seen", "last_seen"}
_SEARCH_LIMIT_PER_CATEGORY = 10


class HostInventoryQueryService:
    """Search/filter/sort/paginate reads across the durable host inventory."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- Hosts -----------------------------------------------------------

    async def list_hosts(
        self,
        *,
        assessment_id: uuid.UUID | None = None,
        target_id: uuid.UUID | None = None,
        host_type: HostType | None = None,
        state: HostState | None = None,
        search: str | None = None,
        sort: Sort | None = None,
        pagination: Pagination | None = None,
    ) -> Page[HostSummaryRead]:
        pagination = pagination or Pagination()
        sort = sort or Sort(field="last_seen", direction=SortDirection.DESC)
        if sort.field not in _HOST_SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort hosts by '{sort.field}'.")

        conditions = [owned_by_active_assessment(DiscoveredHost.assessment_id)]
        if assessment_id is not None:
            conditions.append(DiscoveredHost.assessment_id == assessment_id)
        if target_id is not None:
            conditions.append(DiscoveredHost.target_id == target_id)
        if host_type is not None:
            conditions.append(DiscoveredHost.host_type == host_type)
        if state is not None:
            conditions.append(DiscoveredHost.state == state)
        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append(
                (DiscoveredHost.hostname.ilike(term))
                | (DiscoveredHost.fqdn.ilike(term))
                | (DiscoveredHost.ipv4.ilike(term))
                | (DiscoveredHost.ipv6.ilike(term))
            )

        sort_column = getattr(DiscoveredHost, sort.field)
        order_by = sort_column.desc() if sort.direction == SortDirection.DESC else sort_column.asc()

        total = (await self._session.execute(select(func.count()).select_from(DiscoveredHost).where(*conditions))).scalar_one()
        stmt = select(DiscoveredHost).where(*conditions).order_by(order_by).offset(pagination.offset).limit(pagination.page_size)
        hosts = list((await self._session.execute(stmt)).scalars().all())

        counts: dict[uuid.UUID, int] = {}
        if hosts:
            host_ids = [host.id for host in hosts]
            count_stmt = select(Service.host_id, func.count(Service.id)).where(Service.host_id.in_(host_ids)).group_by(Service.host_id)
            counts = dict((await self._session.execute(count_stmt)).all())

        items = []
        for host in hosts:
            summary = HostSummaryRead.model_validate(host)
            summary.service_count = counts.get(host.id, 0)
            items.append(summary)
        return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    async def get_host(self, host_id: uuid.UUID) -> HostDetailRead:
        stmt = (
            select(DiscoveredHost)
            .options(
                selectinload(DiscoveredHost.network_interfaces),
                selectinload(DiscoveredHost.services),
                selectinload(DiscoveredHost.technologies),
                selectinload(DiscoveredHost.operating_systems),
                selectinload(DiscoveredHost.observations).selectinload(Observation.evidence),
            )
            .where(DiscoveredHost.id == host_id, owned_by_active_assessment(DiscoveredHost.assessment_id))
        )
        host = (await self._session.execute(stmt)).scalar_one_or_none()
        if host is None:
            raise NotFoundError(f"Host {host_id} not found.")

        history_stmt = (
            select(ExecutionHost, ToolExecution, Tool, Target)
            .join(ToolExecution, ToolExecution.id == ExecutionHost.execution_id)
            .join(Tool, Tool.id == ToolExecution.tool_id)
            .join(Target, Target.id == ToolExecution.target_id)
            .where(ExecutionHost.host_id == host_id)
            .order_by(ExecutionHost.created_at.desc())
        )
        history_rows = (await self._session.execute(history_stmt)).all()
        execution_history = [
            ExecutionHistoryEntryRead(
                execution_id=link.execution_id, tool_name=tool.name, target_value=target.target_value,
                is_new=link.is_new, created_at=link.created_at,
            )
            for link, execution, tool, target in history_rows
        ]

        detail = HostDetailRead.model_validate(host)
        detail.execution_history = execution_history
        return detail

    # -- Services -----------------------------------------------------------

    async def list_services(
        self,
        *,
        host_id: uuid.UUID | None = None,
        protocol: NetworkProtocol | None = None,
        state: PortState | None = None,
        port: int | None = None,
        search: str | None = None,
        sort: Sort | None = None,
        pagination: Pagination | None = None,
    ) -> Page[ServiceRead]:
        pagination = pagination or Pagination()
        sort = sort or Sort(field="last_seen", direction=SortDirection.DESC)
        if sort.field not in _SERVICE_SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort services by '{sort.field}'.")

        conditions = [host_owned_by_active_assessment(Service.host_id)]
        if host_id is not None:
            conditions.append(Service.host_id == host_id)
        if protocol is not None:
            conditions.append(Service.protocol == protocol)
        if state is not None:
            conditions.append(Service.state == state)
        if port is not None:
            conditions.append(Service.port == port)
        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append((Service.service_name.ilike(term)) | (Service.product.ilike(term)))

        sort_column = getattr(Service, sort.field)
        order_by = sort_column.desc() if sort.direction == SortDirection.DESC else sort_column.asc()

        total = (await self._session.execute(select(func.count()).select_from(Service).where(*conditions))).scalar_one()
        stmt = select(Service).where(*conditions).order_by(order_by).offset(pagination.offset).limit(pagination.page_size)
        services = list((await self._session.execute(stmt)).scalars().all())

        items = [ServiceRead.model_validate(service) for service in services]
        return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    # -- Technologies -------------------------------------------------------

    async def list_technologies(
        self,
        *,
        host_id: uuid.UUID | None = None,
        category: TechnologyCategory | None = None,
        search: str | None = None,
        sort: Sort | None = None,
        pagination: Pagination | None = None,
    ) -> Page[TechnologyRead]:
        pagination = pagination or Pagination()
        sort = sort or Sort(field="last_seen", direction=SortDirection.DESC)
        if sort.field not in _TECHNOLOGY_SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort technologies by '{sort.field}'.")

        conditions = [host_owned_by_active_assessment(Technology.host_id)]
        if host_id is not None:
            conditions.append(Technology.host_id == host_id)
        if category is not None:
            conditions.append(Technology.category == category)
        if search and search.strip():
            conditions.append(Technology.name.ilike(f"%{search.strip()}%"))

        sort_column = getattr(Technology, sort.field)
        order_by = sort_column.desc() if sort.direction == SortDirection.DESC else sort_column.asc()

        total = (await self._session.execute(select(func.count()).select_from(Technology).where(*conditions))).scalar_one()
        stmt = select(Technology).where(*conditions).order_by(order_by).offset(pagination.offset).limit(pagination.page_size)
        technologies = list((await self._session.execute(stmt)).scalars().all())

        items = [TechnologyRead.model_validate(technology) for technology in technologies]
        return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    # -- Observations ---------------------------------------------------------

    async def list_observations(
        self,
        *,
        host_id: uuid.UUID | None = None,
        service_id: uuid.UUID | None = None,
        category: ObservationCategory | None = None,
        plugin: str | None = None,
        search: str | None = None,
        sort: Sort | None = None,
        pagination: Pagination | None = None,
    ) -> Page[ObservationRead]:
        pagination = pagination or Pagination()
        sort = sort or Sort(field="last_seen", direction=SortDirection.DESC)
        if sort.field not in _OBSERVATION_SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort observations by '{sort.field}'.")

        conditions = [host_owned_by_active_assessment(Observation.host_id)]
        if host_id is not None:
            conditions.append(Observation.host_id == host_id)
        if service_id is not None:
            conditions.append(Observation.service_id == service_id)
        if category is not None:
            conditions.append(Observation.category == category)
        if plugin is not None:
            conditions.append(Observation.plugin == plugin)
        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append((Observation.title.ilike(term)) | (Observation.detail.ilike(term)))

        sort_column = getattr(Observation, sort.field)
        order_by = sort_column.desc() if sort.direction == SortDirection.DESC else sort_column.asc()

        total = (await self._session.execute(select(func.count()).select_from(Observation).where(*conditions))).scalar_one()
        stmt = (
            select(Observation)
            .options(selectinload(Observation.evidence))
            .where(*conditions)
            .order_by(order_by)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        observations = list((await self._session.execute(stmt)).scalars().all())

        items = [ObservationRead.model_validate(observation) for observation in observations]
        return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    # -- Operating Systems ----------------------------------------------------

    async def list_operating_systems(
        self,
        *,
        host_id: uuid.UUID | None = None,
        search: str | None = None,
        sort: Sort | None = None,
        pagination: Pagination | None = None,
    ) -> Page[OperatingSystemRead]:
        pagination = pagination or Pagination()
        sort = sort or Sort(field="accuracy", direction=SortDirection.DESC)
        if sort.field not in _OS_SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort operating systems by '{sort.field}'.")

        conditions = [host_owned_by_active_assessment(OperatingSystem.host_id)]
        if host_id is not None:
            conditions.append(OperatingSystem.host_id == host_id)
        if search and search.strip():
            conditions.append(OperatingSystem.name.ilike(f"%{search.strip()}%"))

        sort_column = getattr(OperatingSystem, sort.field)
        order_by = sort_column.desc() if sort.direction == SortDirection.DESC else sort_column.asc()

        total = (await self._session.execute(select(func.count()).select_from(OperatingSystem).where(*conditions))).scalar_one()
        stmt = select(OperatingSystem).where(*conditions).order_by(order_by).offset(pagination.offset).limit(pagination.page_size)
        rows = list((await self._session.execute(stmt)).scalars().all())

        items = [OperatingSystemRead.model_validate(row) for row in rows]
        return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    # -- Search -----------------------------------------------------------------

    async def search(self, query: str) -> SearchResponse:
        term = f"%{query.strip()}%"
        response = SearchResponse(query=query)
        if not query.strip():
            return response

        host_stmt = (
            select(DiscoveredHost)
            .where(
                (DiscoveredHost.hostname.ilike(term))
                | (DiscoveredHost.fqdn.ilike(term))
                | (DiscoveredHost.ipv4.ilike(term))
                | (DiscoveredHost.ipv6.ilike(term)),
                owned_by_active_assessment(DiscoveredHost.assessment_id),
            )
            .limit(_SEARCH_LIMIT_PER_CATEGORY)
        )
        for host in (await self._session.execute(host_stmt)).scalars().all():
            label = host.hostname or host.ipv4 or host.ipv6 or str(host.id)
            response.hosts.append(
                SearchResult(
                    kind="host", id=host.id, host_id=host.id, assessment_id=host.assessment_id,
                    label=label, detail=host.host_type.value,
                )
            )

        # service/technology/observation carry no assessment_id column of their own -- joined
        # through their owning DiscoveredHost so a search result can still deep-link into the
        # assessment that discovered it, per this UI refactor's contextual-navigation design.
        service_stmt = (
            select(Service, DiscoveredHost.assessment_id)
            .join(DiscoveredHost, DiscoveredHost.id == Service.host_id)
            .where(
                (Service.service_name.ilike(term)) | (Service.product.ilike(term)),
                host_owned_by_active_assessment(Service.host_id),
            )
            .limit(_SEARCH_LIMIT_PER_CATEGORY)
        )
        for service, assessment_id in (await self._session.execute(service_stmt)).all():
            label = f"{service.service_name or 'unknown'} ({service.port}/{service.protocol.value})"
            response.services.append(
                SearchResult(
                    kind="service", id=service.id, host_id=service.host_id, assessment_id=assessment_id,
                    label=label, detail=service.product,
                )
            )

        technology_stmt = (
            select(Technology, DiscoveredHost.assessment_id)
            .join(DiscoveredHost, DiscoveredHost.id == Technology.host_id)
            .where(Technology.name.ilike(term), host_owned_by_active_assessment(Technology.host_id))
            .limit(_SEARCH_LIMIT_PER_CATEGORY)
        )
        for technology, assessment_id in (await self._session.execute(technology_stmt)).all():
            response.technologies.append(
                SearchResult(
                    kind="technology", id=technology.id, host_id=technology.host_id, assessment_id=assessment_id,
                    label=technology.name, detail=technology.version,
                )
            )

        observation_stmt = (
            select(Observation, DiscoveredHost.assessment_id)
            .join(DiscoveredHost, DiscoveredHost.id == Observation.host_id)
            .where(Observation.title.ilike(term), host_owned_by_active_assessment(Observation.host_id))
            .limit(_SEARCH_LIMIT_PER_CATEGORY)
        )
        for observation, assessment_id in (await self._session.execute(observation_stmt)).all():
            response.observations.append(
                SearchResult(
                    kind="observation", id=observation.id, host_id=observation.host_id, assessment_id=assessment_id,
                    label=observation.title, detail=observation.source,
                )
            )

        finding_stmt = (
            select(Finding)
            .where(
                (Finding.title.ilike(term)) | (Finding.description.ilike(term)),
                owned_by_active_assessment(Finding.assessment_id),
            )
            .limit(_SEARCH_LIMIT_PER_CATEGORY)
        )
        for finding in (await self._session.execute(finding_stmt)).scalars().all():
            response.findings.append(
                SearchResult(
                    kind="finding", id=finding.id, host_id=finding.host_id, assessment_id=finding.assessment_id,
                    label=finding.title, detail=finding.severity.value,
                )
            )

        return response
