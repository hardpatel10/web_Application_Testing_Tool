"""Temporary directory helper for plugin authors.

Wraps :func:`tempfile.TemporaryDirectory` so a plugin's ``prepare()``/
``cleanup()`` pair doesn't need to manage cleanup manually or risk leaking
a directory if execution raises partway through.
"""

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def plugin_temp_directory(*, prefix: str = "plugin-") -> Iterator[Path]:
    """Yield a fresh temporary directory, deleted automatically on exit."""
    with tempfile.TemporaryDirectory(prefix=prefix) as directory:
        yield Path(directory)
