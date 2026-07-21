"""Small time-related helper utilities."""

import time


def seconds_since(monotonic_start: float) -> float:
    """Return elapsed seconds since a ``time.monotonic()`` reference point."""
    return time.monotonic() - monotonic_start
