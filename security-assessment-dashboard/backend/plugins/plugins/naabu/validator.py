"""Target validation for Naabu."""

from backend.models.enums import TargetType
from backend.plugins.sdk import is_valid_target

SUPPORTED_TARGET_TYPES = (TargetType.IPV4, TargetType.IPV6, TargetType.CIDR, TargetType.HOSTNAME)


def validate_naabu_target(target_type: TargetType, target_value: str) -> bool:
    return target_type in SUPPORTED_TARGET_TYPES and is_valid_target(target_type, target_value)
