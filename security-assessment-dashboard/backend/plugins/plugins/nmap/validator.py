"""Target validation for Nmap."""

from urllib.parse import urlparse

from backend.models.enums import TargetType
from backend.plugins.sdk import is_valid_target

SUPPORTED_TARGET_TYPES = (
    TargetType.IPV4,
    TargetType.IPV6,
    TargetType.CIDR,
    TargetType.HOSTNAME,
    TargetType.DOMAIN,
    TargetType.URL,
)


def resolve_nmap_target(target_type: TargetType, target_value: str) -> str:
    """Return the value Nmap should actually scan.

    Nmap has no notion of scheme, path, or query string -- a URL target is
    reduced to its bare host (``https://example.com/`` -> ``example.com``)
    before it ever reaches the command builder. Every other supported
    target type is already bare and passes through unchanged.
    """
    if target_type != TargetType.URL:
        return target_value
    return urlparse(target_value).hostname or target_value


def validate_nmap_target(target_type: TargetType, target_value: str) -> bool:
    if target_type not in SUPPORTED_TARGET_TYPES or not is_valid_target(target_type, target_value):
        return False
    if target_type == TargetType.URL:
        return bool(urlparse(target_value).hostname)
    return True
