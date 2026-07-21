"""Per-job structured log files.

Every job gets one combined, timestamped, human-readable log file under
its assessment's existing ``logs/`` subdirectory (see
``backend.core.paths``) -- the durable record ``GET /jobs/{id}/logs``
reads and the frontend's log viewer polls for "live" updates. This
interleaves engine-level milestones (preparing/started/finished) with the
tool's own captured stdout/stderr for one readable timeline; the raw,
unmodified stdout/stderr are additionally kept as their own files
(``ToolExecution.stdout_path``/``stderr_path``) since that is the
permanent source of truth for what the tool actually printed.
"""

from datetime import datetime, timezone
from pathlib import Path


class ExecutionLogger:
    """Appends timestamped lines to one job's log file."""

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._log_path

    def write(self, message: str, *, level: str = "INFO") -> None:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] [{level}] {message}\n")

    def write_block(self, header: str, content: str) -> None:
        if not content:
            return
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"--- {header} ---\n{content.rstrip()}\n--- end {header} ---\n")

    @staticmethod
    def read(log_path: Path, *, tail_lines: int | None = None, search: str | None = None) -> list[str]:
        """Read a job's log file, optionally filtered by a case-insensitive substring and/or tailed."""
        if not log_path.is_file():
            return []
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if search:
            term = search.lower()
            lines = [line for line in lines if term in line.lower()]
        if tail_lines is not None:
            lines = lines[-tail_lines:]
        return lines
