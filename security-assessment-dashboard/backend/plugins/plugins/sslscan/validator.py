"""Target validation for SSLScan."""

from backend.models.enums import TargetType
from backend.plugins.sdk import is_valid_target

SUPPORTED_TARGET_TYPES = (TargetType.HOSTNAME, TargetType.IPV4, TargetType.URL)


def validate_sslscan_target(target_type: TargetType, target_value: str) -> bool:
    return target_type in SUPPORTED_TARGET_TYPES and is_valid_target(target_type, target_value)
