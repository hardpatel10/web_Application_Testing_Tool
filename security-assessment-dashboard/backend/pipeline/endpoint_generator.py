"""Turns a discovered host + service into the URL a follow-up scanner should target.

Never the assessment's original target string -- always the specific
endpoint Nmap actually discovered, per the Assessment Pipeline brief:
"Nikto must NOT scan the original assessment target. It must scan only the
HTTP/HTTPS endpoints identified by Nmap."
"""

from backend.models.discovered_host import DiscoveredHost
from backend.models.service import Service

_DEFAULT_PORT = {"http": 80, "https": 443}


def _host_address(host: DiscoveredHost) -> str:
    """Prefer a name a scanner can resolve/present nicely; fall back to the raw IP."""
    return host.hostname or host.fqdn or host.ipv4 or host.ipv6 or ""


def generate_endpoint(host: DiscoveredHost, service: Service, *, scheme: str) -> str:
    """Build ``http(s)://host[:port]`` -- the port is omitted only when it's the scheme's own default."""
    address = _host_address(host)
    if service.port == _DEFAULT_PORT.get(scheme):
        return f"{scheme}://{address}"
    return f"{scheme}://{address}:{service.port}"
