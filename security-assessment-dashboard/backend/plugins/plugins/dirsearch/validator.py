"""Target validation for Dirsearch."""

from backend.models.enums import TargetType
from backend.plugins.sdk import is_valid_target

SUPPORTED_TARGET_TYPES = (TargetType.URL,)


def validate_dirsearch_target(target_type: TargetType, target_value: str) -> bool:
    return target_type in SUPPORTED_TARGET_TYPES and is_valid_target(target_type, target_value)
