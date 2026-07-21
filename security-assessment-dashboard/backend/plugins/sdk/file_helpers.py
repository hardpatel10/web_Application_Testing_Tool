"""Filesystem helpers for plugin authors.

Thin ``pathlib`` wrappers only — plugins never need arbitrary filesystem
access beyond reading/writing within their own execution context's
``output_directory``, so nothing here reaches outside a given path.
"""

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Create ``path`` (and parents) if missing. Idempotent."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text_file(path: Path, *, encoding: str = "utf-8") -> str | None:
    """Read ``path`` as text, returning ``None`` if it doesn't exist or can't be decoded."""
    try:
        return path.read_text(encoding=encoding)
    except (OSError, UnicodeDecodeError):
        return None


def write_text_file(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Write ``content`` to ``path``, creating parent directories if needed."""
    ensure_directory(path.parent)
    path.write_text(content, encoding=encoding)
