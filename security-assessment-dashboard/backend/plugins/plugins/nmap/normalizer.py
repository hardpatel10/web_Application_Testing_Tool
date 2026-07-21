"""Normalizes parsed Nmap output into the platform's common shape.

Produces hosts and observations only — per ``.claude/CLAUDE.md``
and this phase's explicit instruction, this never generates a vulnerability,
never assigns a CVSS score, and never fabricates a finding. Even NSE
scripts named ``smb-vuln-*`` are recorded as a plain, neutral observation
(the script's own raw output text) — this platform does not additionally
judge, score, or grade what the script reported.

Passes through *every* address and *every* OS candidate Nmap reports
(``NormalizedAddress``/``NormalizedOsMatch``, both lists) rather than
picking a single "best" one — see ``backend.plugins.models.normalized``.
"""

from backend.models.enums import HostState, NetworkProtocol, ObservationCategory, PortState, TargetType
from backend.plugins.models.normalized import (
    NormalizedAddress,
    NormalizedHost,
    NormalizedObservation,
    NormalizedOsMatch,
    NormalizedOutput,
    NormalizedService,
)

from .parser import NmapHost, NmapScanResult

_STATE_MAP = {"up": HostState.UP, "down": HostState.DOWN}

#: Best-effort, honest categorization of a script by its well-known NSE id
#: prefix -- neutral metadata grouping, not a vulnerability judgment. Any
#: script id not matched here stays ObservationCategory.OTHER.
_CATEGORY_PREFIXES: tuple[tuple[str, ObservationCategory], ...] = (
    ("ssl-", ObservationCategory.TLS),
    ("tls-", ObservationCategory.TLS),
    ("http-", ObservationCategory.WEB),
    ("smb-", ObservationCategory.NETWORK),
    ("smb2-", ObservationCategory.NETWORK),
    ("ssh-", ObservationCategory.AUTH),
    ("ftp-", ObservationCategory.AUTH),
    ("dns-", ObservationCategory.NETWORK),
    ("snmp-", ObservationCategory.CONFIGURATION),
    ("rdp-", ObservationCategory.NETWORK),
    ("mysql-", ObservationCategory.CONFIGURATION),
    ("ms-sql-", ObservationCategory.CONFIGURATION),
)


def _categorize(script_id: str) -> ObservationCategory:
    for prefix, category in _CATEGORY_PREFIXES:
        if script_id.startswith(prefix):
            return category
    return ObservationCategory.OTHER


def normalize_nmap_output(parsed_output: NmapScanResult | None) -> NormalizedOutput:
    if parsed_output is None:
        return NormalizedOutput()

    hosts: list[NormalizedHost] = []
    observations: list[NormalizedObservation] = []

    for index, host in enumerate(parsed_output.hosts):
        hosts.append(_normalize_host(host))
        observations.extend(_normalize_observations(host, host_index=index))

    return NormalizedOutput(hosts=hosts, observations=observations)


def _normalize_host(host: NmapHost) -> NormalizedHost:
    addresses = [
        NormalizedAddress(ip_address=addr, version=TargetType.IPV4 if addr_type == "ipv4" else TargetType.IPV6)
        for addr, addr_type in host.addresses
        if addr_type in ("ipv4", "ipv6")
    ]
    mac_address = next((addr for addr, addr_type in host.addresses if addr_type == "mac"), None)

    return NormalizedHost(
        hostname=host.hostnames[0] if host.hostnames else None,
        fqdn=host.hostnames[0] if host.hostnames else None,
        addresses=addresses,
        mac_address=mac_address,
        mac_vendor=host.mac_vendor,
        state=_STATE_MAP.get(host.status, HostState.UNKNOWN),
        os_matches=[NormalizedOsMatch(name=match.name, accuracy=match.accuracy) for match in host.os_matches],
        services=[
            NormalizedService(
                port=port.port,
                protocol=NetworkProtocol(port.protocol) if port.protocol in ("tcp", "udp") else NetworkProtocol.TCP,
                state=PortState(port.state) if port.state in PortState._value2member_map_ else PortState.FILTERED,
                service_name=port.service_name,
                product=port.product,
                version=port.version,
                extra_info=port.extra_info,
            )
            for port in host.ports
        ],
    )


def _normalize_observations(host: NmapHost, *, host_index: int) -> list[NormalizedObservation]:
    observations = [
        NormalizedObservation(
            source=script.script_id,
            title=script.script_id,
            detail=script.output,
            host_index=host_index,
            category=_categorize(script.script_id).value,
            observation_type=script.script_id,
        )
        for script in host.host_scripts
    ]
    for port in host.ports:
        observations.extend(
            NormalizedObservation(
                source=script.script_id,
                title=f"{script.script_id} ({port.protocol}/{port.port})",
                detail=script.output,
                host_index=host_index,
                port=port.port,
                category=_categorize(script.script_id).value,
                observation_type=script.script_id,
            )
            for script in port.scripts
        )
    return observations
