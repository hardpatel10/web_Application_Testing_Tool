"""Target validation for Nuclei."""

from backend.models.enums import TargetType
from backend.plugins.sdk import is_valid_target

SUPPORTED_TARGET_TYPES = (TargetType.URL, TargetType.HOSTNAME, TargetType.DOMAIN, TargetType.IPV4)


def validate_nuclei_target(target_type: TargetType, target_value: str) -> bool:
    return target_type in SUPPORTED_TARGET_TYPES and is_valid_target(target_type, target_value)
