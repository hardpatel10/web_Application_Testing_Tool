"""Security-related utilities.

Phase 1 does not implement authentication or authorization. This module
provides the foundational primitives that later auth work will depend
on: secret key generation/validation and redaction of sensitive values
before they reach logs.
"""

import secrets

_MIN_SECRET_KEY_LENGTH = 32
_INSECURE_DEFAULTS = {"dev-insecure-secret-key-change-me", "changeme", "secret"}


def generate_secret_key() -> str:
    """Generate a cryptographically secure random secret key."""
    return secrets.token_urlsafe(48)


def is_secret_key_weak(secret_key: str) -> bool:
    """Return True if the configured secret key is missing, short, or a known default."""
    if not secret_key:
        return True
    if len(secret_key) < _MIN_SECRET_KEY_LENGTH:
        return True
    if secret_key.lower() in _INSECURE_DEFAULTS:
        return True
    return False


def redact(value: str, *, visible_chars: int = 4) -> str:
    """Mask a sensitive string, keeping only the trailing characters visible.

    Intended for safely referencing secrets in logs (e.g. confirming a
    key was loaded without exposing it).
    """
    if len(value) <= visible_chars:
        return "*" * len(value)
    return f"{'*' * (len(value) - visible_chars)}{value[-visible_chars:]}"
