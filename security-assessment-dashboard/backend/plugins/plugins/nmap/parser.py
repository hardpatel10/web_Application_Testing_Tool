"""Parses Nmap's ``-oX`` XML report — never its human-oriented console text.

Extracts hosts, addresses, hostnames, ports, protocols, services,
products, versions, operating systems, and both host-level and port-level
NSE script output, into a small set of plugin-internal dataclasses
consumed only by ``normalizer.py`` in this same package.
"""

from dataclasses import dataclass, field
from xml.etree.ElementTree import Element  # noqa: S405 - type only, parsing goes through defusedxml below

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import safe_xml_parse


@dataclass
class NmapScript:
    """One NSE script result, host- or port-scoped."""

    script_id: str
    output: str


@dataclass
class NmapPort:
    """One scanned port on a host."""

    port: int
    protocol: str
    state: str
    service_name: str | None = None
    product: str | None = None
    version: str | None = None
    extra_info: str | None = None
    scripts: list[NmapScript] = field(default_factory=list)


@dataclass
class NmapOsMatch:
    name: str
    accuracy: int


@dataclass
class NmapHost:
    """One ``<host>`` element: everything Nmap reported about one target."""

    status: str = "unknown"
    addresses: list[tuple[str, str]] = field(default_factory=list)  # (addr, addrtype: ipv4/ipv6/mac)
    mac_vendor: str | None = None
    hostnames: list[str] = field(default_factory=list)
    os_matches: list[NmapOsMatch] = field(default_factory=list)
    ports: list[NmapPort] = field(default_factory=list)
    host_scripts: list[NmapScript] = field(default_factory=list)


@dataclass
class NmapScanResult:
    """The fully parsed contents of one Nmap XML report."""

    hosts: list[NmapHost] = field(default_factory=list)


def parse_nmap_output(raw_output: PluginRawOutput) -> NmapScanResult | None:
    """Parse Nmap's XML report (on stdout, via ``-oX -``). Returns ``None`` on any parse failure."""
    root = safe_xml_parse(raw_output.stdout)
    if root is None:
        return None
    return NmapScanResult(hosts=[_parse_host(host_element) for host_element in root.findall("host")])


def _parse_host(host_element: Element) -> NmapHost:
    host = NmapHost()

    status_element = host_element.find("status")
    if status_element is not None:
        host.status = status_element.get("state", "unknown")

    for address_element in host_element.findall("address"):
        addr = address_element.get("addr")
        addr_type = address_element.get("addrtype", "ipv4")
        if addr:
            host.addresses.append((addr, addr_type))
        if addr_type == "mac" and address_element.get("vendor"):
            host.mac_vendor = address_element.get("vendor")

    hostnames_element = host_element.find("hostnames")
    if hostnames_element is not None:
        for hostname_element in hostnames_element.findall("hostname"):
            name = hostname_element.get("name")
            if name:
                host.hostnames.append(name)

    os_element = host_element.find("os")
    if os_element is not None:
        for match_element in os_element.findall("osmatch"):
            name = match_element.get("name")
            accuracy = match_element.get("accuracy")
            if name and accuracy is not None:
                try:
                    host.os_matches.append(NmapOsMatch(name=name, accuracy=int(accuracy)))
                except ValueError:
                    continue

    hostscript_element = host_element.find("hostscript")
    if hostscript_element is not None:
        host.host_scripts = _parse_scripts(hostscript_element)

    ports_element = host_element.find("ports")
    if ports_element is not None:
        for port_element in ports_element.findall("port"):
            host.ports.append(_parse_port(port_element))

    return host


def _parse_port(port_element: Element) -> NmapPort:
    port_id = port_element.get("portid", "0")
    protocol = port_element.get("protocol", "tcp")

    state_element = port_element.find("state")
    state = state_element.get("state", "unknown") if state_element is not None else "unknown"

    service_element = port_element.find("service")
    service_name = product = version = extra_info = None
    if service_element is not None:
        service_name = service_element.get("name")
        product = service_element.get("product")
        version = service_element.get("version")
        extra_info = service_element.get("extrainfo")

    return NmapPort(
        port=int(port_id) if port_id.isdigit() else 0,
        protocol=protocol,
        state=state,
        service_name=service_name,
        product=product,
        version=version,
        extra_info=extra_info,
        scripts=_parse_scripts(port_element),
    )


def _parse_scripts(parent_element: Element) -> list[NmapScript]:
    scripts = []
    for script_element in parent_element.findall("script"):
        script_id = script_element.get("id")
        output = script_element.get("output", "")
        if script_id:
            scripts.append(NmapScript(script_id=script_id, output=output))
    return scripts
