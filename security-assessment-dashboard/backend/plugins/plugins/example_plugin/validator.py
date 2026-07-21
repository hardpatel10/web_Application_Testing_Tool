"""Target validation for the example plugin.

A real plugin's ``validator.py`` typically narrows the SDK's generic
target validation to whatever subset of target types/values the
underlying tool actually accepts.
"""

from backend.models.enums import TargetType
from backend.plugins.sdk import is_valid_target

_SUPPORTED_TARGET_TYPES = (TargetType.HOSTNAME, TargetType.IPV4)


def validate_example_target(target_type: TargetType, target_value: str) -> bool:
    """Return whether this plugin can run against the given target."""
    return target_type in _SUPPORTED_TARGET_TYPES and is_valid_target(target_type, target_value)
