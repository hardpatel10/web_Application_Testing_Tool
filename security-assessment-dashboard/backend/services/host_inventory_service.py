"""The Host Inventory & Observation Engine's merge/upsert layer.

The *only* place a :class:`~backend.plugins.models.normalized.NormalizedOutput`
becomes persisted ``DiscoveredHost``/``NetworkInterface``/``Service``/``Technology``/
``OperatingSystem``/``Observation``/``ObservationEvidence`` rows — replaces
Phase 7's inline logic in ``backend.workers.manager.ExecutionManager``, which
always inserted brand-new host rows with no lookup against prior scans.
Keeps the workers package tool-agnostic-dispatch-only (its stated
architectural role); this is where the actual domain logic lives, exactly
like every other service in this codebase.

Merge algorithm, per completed job, inside one DB transaction: resolve the
owning ``Target`` from the ``ToolExecution`` (every execution runs against
exactly one target -- see ``backend.models.tool_execution``), then for every
:class:`~backend.plugins.models.normalized.NormalizedHost`, compute its
deterministic fingerprint (:mod:`backend.services.fingerprinting`) and look
up an existing ``DiscoveredHost`` with that ``(target_id, fingerprint)`` --
found means "update `last_seen` and backfill", not found means "insert new,
`first_seen = last_seen = now`". A host is a child of the target that
discovered it (per ``.claude/CLAUDE.md``'s corrected domain model), not a
top-level sibling of ``Target`` under the assessment -- the same physical
host rediscovered via a *different* target is intentionally a separate
``DiscoveredHost`` row, since each target's scan history is tracked on its
own. Services/Technologies/OperatingSystems/Observations follow the same
find-or-insert-or-update shape, each scoped to its owning host. Every
completed job also gets one ``ExecutionHost``/``ExecutionObservation`` row
per host/observation it touched (``is_new`` distinguishing first discovery
from a re-confirmation) — the durable execution-history record
``ToolExecution`` itself no longer owns directly.

Per ``.claude/CLAUDE.md``: stores facts only. No severity, no CVSS, no
``Finding`` row is ever created or touched here.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.base import utcnow
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import HostState, HostType, ObservationCategory, TargetType, TechnologyCategory
from backend.models.execution_host import ExecutionHost
from backend.models.execution_observation import ExecutionObservation
from backend.models.network_interface import NetworkInterface
from backend.models.observation import Observation
from backend.models.observation_evidence import ObservationEvidence
from backend.models.operating_system import OperatingSystem
from backend.models.service import Service
from backend.models.technology import Technology
from backend.models.tool_execution import ToolExecution
from backend.plugins.models.normalized import NormalizedHost, NormalizedOutput
from backend.services import fingerprinting


@dataclass
class PersistSummary:
    """Counts of what a :meth:`HostInventoryService.persist` call actually did — for logging."""

    hosts_created: int = 0
    hosts_updated: int = 0
    hosts_skipped: int = 0
    services_created: int = 0
    services_updated: int = 0
    technologies_created: int = 0
    technologies_updated: int = 0
    operating_systems_created: int = 0
    operating_systems_updated: int = 0
    observations_created: int = 0
    observations_updated: int = 0


class HostInventoryService:
    """Merges one job's normalized output into the durable, deduplicated inventory."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist(
        self,
        *,
        assessment_id: uuid.UUID,
        execution_id: uuid.UUID,
        plugin_name: str,
        normalized: NormalizedOutput,
    ) -> PersistSummary:
        now = utcnow()
        summary = PersistSummary()
        target_id = await self._resolve_target_id(execution_id)

        # Parallel to normalized.hosts: the persisted DiscoveredHost for each
        # index (or None if that entry had no usable identity signal), and
        # each host's fingerprint + a port->Service map, so the observation
        # pass below can resolve NormalizedObservation.host_index/port to
        # real foreign keys.
        hosts_by_index: list[DiscoveredHost | None] = []
        fingerprints_by_index: list[str | None] = []
        services_by_host: dict[uuid.UUID, dict[int, Service]] = {}
        touched_hosts_this_run: set[str] = set()

        for normalized_host in normalized.hosts:
            host, host_fp, host_was_created = await self._upsert_host(
                assessment_id=assessment_id,
                target_id=target_id,
                execution_id=execution_id,
                normalized_host=normalized_host,
                now=now,
                summary=summary,
            )
            hosts_by_index.append(host)
            fingerprints_by_index.append(host_fp)
            if host is None:
                continue

            if host_fp not in touched_hosts_this_run:
                touched_hosts_this_run.add(host_fp)
                await self._link_execution_host(execution_id, host.id, is_new=host_was_created)

            port_map: dict[int, Service] = {}
            for normalized_service in normalized_host.services:
                service = await self._upsert_service(
                    host=host, host_fingerprint_value=host_fp, normalized_service=normalized_service, now=now, summary=summary
                )
                port_map[service.port] = service
                if normalized_service.product:
                    await self._upsert_technology(
                        host=host, service=service, execution_id=execution_id, product=normalized_service.product,
                        version=normalized_service.version, now=now, summary=summary,
                    )
            services_by_host[host.id] = port_map

            for os_match in normalized_host.os_matches:
                await self._upsert_operating_system(
                    host=host, execution_id=execution_id, name=os_match.name, accuracy=os_match.accuracy,
                    vendor=os_match.vendor, family=os_match.family, now=now, summary=summary,
                )

        for normalized_observation in normalized.observations:
            host = None
            host_fp = "none"
            if (
                normalized_observation.host_index is not None
                and 0 <= normalized_observation.host_index < len(hosts_by_index)
            ):
                host = hosts_by_index[normalized_observation.host_index]
                host_fp = fingerprints_by_index[normalized_observation.host_index] or "none"

            service = None
            if host is not None and normalized_observation.port is not None:
                service = services_by_host.get(host.id, {}).get(normalized_observation.port)

            await self._upsert_observation(
                execution_id=execution_id,
                plugin_name=plugin_name,
                host=host,
                host_fingerprint_value=host_fp,
                service=service,
                now=now,
                summary=summary,
                source=normalized_observation.source,
                category=normalized_observation.category,
                observation_type=normalized_observation.observation_type,
                title=normalized_observation.title,
                detail=normalized_observation.detail,
                port=normalized_observation.port,
            )

        return summary

    async def _resolve_target_id(self, execution_id: uuid.UUID) -> uuid.UUID:
        """Every execution runs against exactly one target -- see ``ToolExecution.target_id``."""
        execution = await self._session.get(ToolExecution, execution_id)
        return execution.target_id

    # -- DiscoveredHost ---------------------------------------------------------

    async def _upsert_host(
        self,
        *,
        assessment_id: uuid.UUID,
        target_id: uuid.UUID,
        execution_id: uuid.UUID,
        normalized_host: NormalizedHost,
        now,
        summary: PersistSummary,
    ) -> tuple[DiscoveredHost | None, str | None, bool]:
        ipv4 = next((a.ip_address for a in normalized_host.addresses if a.version == TargetType.IPV4), None)
        ipv6 = next((a.ip_address for a in normalized_host.addresses if a.version == TargetType.IPV6), None)

        try:
            host_fp = fingerprinting.host_fingerprint(
                mac_address=normalized_host.mac_address, ipv4=ipv4, ipv6=ipv6, hostname=normalized_host.hostname
            )
        except ValueError:
            summary.hosts_skipped += 1
            return None, None, False

        existing = (
            await self._session.execute(
                select(DiscoveredHost).where(DiscoveredHost.target_id == target_id, DiscoveredHost.fingerprint == host_fp)
            )
        ).scalar_one_or_none()

        if existing is None:
            host = DiscoveredHost(
                target_id=target_id,
                assessment_id=assessment_id,
                hostname=normalized_host.hostname,
                fqdn=normalized_host.fqdn,
                ipv4=ipv4,
                ipv6=ipv6,
                mac_address=normalized_host.mac_address,
                mac_vendor=normalized_host.mac_vendor,
                host_type=HostType.HOST,
                state=normalized_host.state,
                fingerprint=host_fp,
                first_seen=now,
                last_seen=now,
                source_execution_id=execution_id,
            )
            self._session.add(host)
            await self._session.flush()
            summary.hosts_created += 1
            was_created = True
        else:
            host = existing
            host.last_seen = now
            host.hostname = host.hostname or normalized_host.hostname
            host.fqdn = host.fqdn or normalized_host.fqdn
            host.ipv4 = host.ipv4 or ipv4
            host.ipv6 = host.ipv6 or ipv6
            host.mac_address = host.mac_address or normalized_host.mac_address
            host.mac_vendor = host.mac_vendor or normalized_host.mac_vendor
            if normalized_host.state != HostState.UNKNOWN:
                host.state = normalized_host.state
            summary.hosts_updated += 1
            was_created = False

        await self._upsert_network_interfaces(host, normalized_host)
        return host, host_fp, was_created

    async def _upsert_network_interfaces(self, host: DiscoveredHost, normalized_host: NormalizedHost) -> None:
        existing_addresses = {
            row[0]
            for row in (
                await self._session.execute(select(NetworkInterface.ip_address).where(NetworkInterface.host_id == host.id))
            ).all()
        }
        for address in normalized_host.addresses:
            if address.ip_address in existing_addresses:
                continue
            self._session.add(
                NetworkInterface(
                    host_id=host.id,
                    ip_address=address.ip_address,
                    version=address.version,
                    mac_address=address.mac_address or normalized_host.mac_address,
                )
            )
            existing_addresses.add(address.ip_address)

    async def _link_execution_host(self, execution_id: uuid.UUID, host_id: uuid.UUID, *, is_new: bool) -> None:
        self._session.add(ExecutionHost(execution_id=execution_id, host_id=host_id, is_new=is_new))

    # -- Service / Technology / OperatingSystem --------------------------------

    async def _upsert_service(self, *, host: DiscoveredHost, host_fingerprint_value: str, normalized_service, now, summary: PersistSummary) -> Service:
        service_fp = fingerprinting.service_fingerprint(
            host_fingerprint_value=host_fingerprint_value, port=normalized_service.port, protocol=normalized_service.protocol
        )
        existing = (
            await self._session.execute(select(Service).where(Service.host_id == host.id, Service.fingerprint == service_fp))
        ).scalar_one_or_none()

        if existing is None:
            service = Service(
                host_id=host.id,
                port=normalized_service.port,
                protocol=normalized_service.protocol,
                state=normalized_service.state,
                service_name=normalized_service.service_name,
                product=normalized_service.product,
                version=normalized_service.version,
                extra_info=normalized_service.extra_info,
                banner=normalized_service.banner,
                fingerprint=service_fp,
                first_seen=now,
                last_seen=now,
            )
            self._session.add(service)
            await self._session.flush()
            summary.services_created += 1
        else:
            service = existing
            service.state = normalized_service.state
            service.service_name = normalized_service.service_name or service.service_name
            service.product = normalized_service.product or service.product
            service.version = normalized_service.version or service.version
            service.extra_info = normalized_service.extra_info or service.extra_info
            service.banner = normalized_service.banner or service.banner
            service.last_seen = now
            summary.services_updated += 1
        return service

    async def _upsert_technology(
        self, *, host: DiscoveredHost, service: Service, execution_id: uuid.UUID, product: str, version: str | None, now, summary: PersistSummary
    ) -> None:
        existing = (
            await self._session.execute(
                select(Technology).where(
                    Technology.host_id == host.id, Technology.service_id == service.id, Technology.name == product
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            self._session.add(
                Technology(
                    host_id=host.id,
                    service_id=service.id,
                    name=product,
                    version=version,
                    category=TechnologyCategory.OTHER,
                    first_seen=now,
                    last_seen=now,
                    source_execution_id=execution_id,
                )
            )
            summary.technologies_created += 1
        else:
            existing.version = version or existing.version
            existing.last_seen = now
            summary.technologies_updated += 1

    async def _upsert_operating_system(
        self, *, host: DiscoveredHost, execution_id: uuid.UUID, name: str, accuracy: int, vendor: str | None, family: str | None, now, summary: PersistSummary
    ) -> None:
        existing = (
            await self._session.execute(
                select(OperatingSystem).where(
                    OperatingSystem.host_id == host.id, OperatingSystem.name == name, OperatingSystem.version.is_(None)
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            self._session.add(
                OperatingSystem(
                    host_id=host.id,
                    vendor=vendor,
                    family=family,
                    name=name,
                    version=None,
                    accuracy=accuracy,
                    source="nmap-os-detection",
                    first_seen=now,
                    last_seen=now,
                    source_execution_id=execution_id,
                )
            )
            summary.operating_systems_created += 1
        else:
            existing.accuracy = accuracy
            existing.last_seen = now
            summary.operating_systems_updated += 1

    # -- Observation ------------------------------------------------------------

    async def _upsert_observation(
        self,
        *,
        execution_id: uuid.UUID,
        plugin_name: str,
        host: DiscoveredHost | None,
        host_fingerprint_value: str,
        service: Service | None,
        now,
        summary: PersistSummary,
        source: str,
        category: str,
        observation_type: str | None,
        title: str,
        detail: str | None,
        port: int | None,
    ) -> None:
        observation_fp = fingerprinting.observation_fingerprint(
            plugin=plugin_name,
            host_fingerprint_value=host_fingerprint_value,
            category=category,
            observation_type=observation_type,
            title=title,
        )

        existing = None
        if host is not None:
            existing = (
                await self._session.execute(
                    select(Observation).where(Observation.host_id == host.id, Observation.fingerprint == observation_fp)
                )
            ).scalar_one_or_none()

        try:
            category_enum = ObservationCategory(category)
        except ValueError:
            category_enum = ObservationCategory.OTHER

        if existing is None:
            observation = Observation(
                execution_id=execution_id,
                host_id=host.id if host else None,
                service_id=service.id if service else None,
                port=port,
                plugin=plugin_name,
                source=source,
                category=category_enum,
                observation_type=observation_type,
                title=title,
                detail=detail,
                fingerprint=observation_fp,
                first_seen=now,
                last_seen=now,
            )
            self._session.add(observation)
            await self._session.flush()
            summary.observations_created += 1
            is_new = True
        else:
            observation = existing
            observation.execution_id = execution_id
            observation.last_seen = now
            summary.observations_updated += 1
            is_new = False

        self._session.add(ExecutionObservation(execution_id=execution_id, observation_id=observation.id, is_new=is_new))
        self._session.add(
            ObservationEvidence(observation_id=observation.id, source_tool=plugin_name, title=source, content=detail)
        )
