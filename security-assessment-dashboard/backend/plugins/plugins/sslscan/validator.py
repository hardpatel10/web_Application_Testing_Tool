"""Target validation and resolution for SSLScan.

SSLScan tests one TLS/SSL-enabled endpoint by attempting a real TLS
handshake -- a URL's scheme is irrelevant to it, so only the host[:port]
is ever extracted from one, mirroring ``nikto/validator.py``'s own
URL-to-host/port reduction. Per the Assessment Pipeline brief, SSLScan is
only ever *automatically* scheduled against a service Nmap already
confirmed is HTTPS/TLS (see ``backend/pipeline/rules/web_rules.py``) --
this validator only checks that a target's *shape* (hostname/domain/
IPv4/IPv6/URL) is one SSLScan can address at all, the same scope every
other plugin's validator has.
"""

from dataclasses import dataclass
from urllib.parse import urlparse

from backend.models.enums import TargetType
from backend.plugins.sdk import is_valid_target

SUPPORTED_TARGET_TYPES = (TargetType.HOSTNAME, TargetType.DOMAIN, TargetType.IPV4, TargetType.IPV6, TargetType.URL)


def validate_sslscan_target(target_type: TargetType, target_value: str) -> bool:
    return target_type in SUPPORTED_TARGET_TYPES and is_valid_target(target_type, target_value)


@dataclass(frozen=True)
class ResolvedSslscanTarget:
    """A target broken into what SSLScan's own CLI needs: a bare host, an optional port, an optional IP version."""

    host: str
    port: int | None = None
    ip_version: str | None = None


def resolve_sslscan_target(target_type: TargetType, target_value: str) -> ResolvedSslscanTarget:
    """Reduce any supported target shape to the bare host/port/ip-version facts SSLScan's CLI needs."""
    if target_type == TargetType.URL:
        parsed = urlparse(target_value)
        return ResolvedSslscanTarget(host=parsed.hostname or target_value, port=parsed.port)
    if target_type == TargetType.IPV6:
        return ResolvedSslscanTarget(host=target_value, ip_version="6")
    if target_type == TargetType.IPV4:
        return ResolvedSslscanTarget(host=target_value, ip_version="4")
    return ResolvedSslscanTarget(host=target_value)
