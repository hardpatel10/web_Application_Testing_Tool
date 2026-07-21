"""Target validation for the dummy execution plugin.

Accepts every target type -- this is a pure execution-engine test fixture,
not a real tool with actual target constraints.
"""

from backend.models.enums import TargetType


def validate_dummy_target(target_type: TargetType, target_value: str) -> bool:
    """Return whether this plugin can run against the given target. Always true."""
    return bool(target_value)
