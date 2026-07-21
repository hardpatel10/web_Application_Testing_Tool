"""JSON helpers for plugin output parsers.

Thin, stdlib-only wrappers that turn ``json``'s exceptions into ``None``
so a plugin's ``parser.py`` can express "malformed output" without a
try/except block of its own.
"""

import json
from typing import Any


def safe_json_loads(text: str) -> Any | None:
    """Parse ``text`` as JSON, returning ``None`` on any parse failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def safe_json_dumps(value: Any, *, indent: int | None = None) -> str | None:
    """Serialize ``value`` to a JSON string, returning ``None`` if it isn't serializable."""
    try:
        return json.dumps(value, indent=indent)
    except (TypeError, ValueError):
        return None


def parse_json_lines(text: str) -> list[Any]:
    """Parse newline-delimited JSON (the common output shape for most Go-based scanners).

    Lines that fail to parse are skipped rather than aborting the whole
    result — one malformed line shouldn't discard everything else a tool
    produced.
    """
    results = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = safe_json_loads(stripped)
        if parsed is not None:
            results.append(parsed)
    return results
