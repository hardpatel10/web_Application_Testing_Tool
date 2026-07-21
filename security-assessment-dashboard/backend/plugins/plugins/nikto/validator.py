"""Target validation and resolution for Nikto.

Nikto scans a web server reachable over HTTP/HTTPS -- that's a URL scheme,
not a distinct ``TargetType``, so a plain hostname or domain is accepted
too (Nikto defaults to port 80/HTTP when given a bare host).
"""

from dataclasses import dataclass
from urllib.parse import urlparse

from backend.models.enums import TargetType
from backend.plugins.sdk import is_valid_target

SUPPORTED_TARGET_TYPES = (TargetType.URL, TargetType.HOSTNAME, TargetType.DOMAIN)


def validate_nikto_target(target_type: TargetType, target_value: str) -> bool:
    return target_type in SUPPORTED_TARGET_TYPES and is_valid_target(target_type, target_value)


@dataclass(frozen=True)
class ResolvedNiktoTarget:
    """A target broken into what Nikto's own flags need: ``-h``, ``-p``, ``-ssl``."""

    host: str
    port: str | None = None
    use_ssl: bool = False


def resolve_nikto_target(target_type: TargetType, target_value: str) -> ResolvedNiktoTarget:
    """Reduce a URL target to bare host/port/scheme facts; hostnames/domains pass through as-is."""
    if target_type == TargetType.URL:
        parsed = urlparse(target_value)
        return ResolvedNiktoTarget(
            host=parsed.hostname or target_value,
            port=str(parsed.port) if parsed.port else None,
            use_ssl=parsed.scheme == "https",
        )
    return ResolvedNiktoTarget(host=target_value)
