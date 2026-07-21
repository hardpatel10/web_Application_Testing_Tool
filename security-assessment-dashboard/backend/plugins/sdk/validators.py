"""Target validation helpers for plugin authors.

Delegates entirely to :mod:`backend.utils.target_validators` — the single,
stdlib-only definition of "what makes a valid IPv4/IPv6/CIDR/hostname/
domain/URL" in this codebase (see ``DECISIONS.md``, Phase 3). Plugin
authors get a small, forgiving boolean/normalizing surface here instead of
needing to catch ``TargetValidationError`` themselves.
"""

from backend.models.enums import TargetType
from backend.utils import target_validators


def is_valid_target(target_type: TargetType, target_value: str) -> bool:
    """Return whether ``target_value`` is valid for ``target_type``."""
    try:
        target_validators.validate_target(target_type, target_value)
    except target_validators.TargetValidationError:
        return False
    return True


def normalize_target(target_type: TargetType, target_value: str) -> str | None:
    """Return the canonical form of ``target_value``, or ``None`` if invalid."""
    try:
        return target_validators.validate_target(target_type, target_value)
    except target_validators.TargetValidationError:
        return None


def detect_target_type(target_value: str) -> TargetType | None:
    """Best-effort auto-detection of a target's type from its raw string."""
    return target_validators.detect_target_type(target_value)
