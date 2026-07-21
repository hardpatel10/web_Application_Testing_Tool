"""Real, secure asyncio subprocess execution for plugins that run a real tool.

The one place in the whole codebase where a plugin's ``execute()`` should
ever start an external program. Always ``asyncio.create_subprocess_exec``
with an explicit argv list -- never ``shell=True`` and never a string
command line -- so a target value embedded in ``command`` (e.g. a
hostname or URL) can never be interpreted as a shell metacharacter.

No plugin calls this yet (the 15 detection-only plugins' ``execute()``
always refuses, and ``DummyExecutionPlugin`` deliberately never runs an
external program at all -- see its docstring) but this is the real,
directly-tested implementation a future tool-integration phase's
``execute()`` methods will call into.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_TERMINATE_GRACE_SECONDS = 5.0


@dataclass(frozen=True)
class ProcessResult:
    """Captured result of one subprocess run."""

    stdout: str
    stderr: str
    return_code: int | None
    timed_out: bool
    duration_seconds: float


async def run_subprocess(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
    on_process_started: Callable[[asyncio.subprocess.Process], None] | None = None,
) -> ProcessResult:
    """Run ``command`` and capture its stdout/stderr/return code.

    ``on_process_started`` is called synchronously with the live
    ``asyncio.subprocess.Process`` the instant it is spawned -- the
    execution engine uses this to register the handle for later
    cancel/kill, without this function needing any knowledge of jobs,
    queues, or the database.

    On timeout, the process is terminated (then killed if it does not
    exit within a short grace period) and ``timed_out=True`` is returned
    rather than raising, so a caller can persist a ``TIMEOUT`` job status
    instead of handling an exception.
    """
    started = time.monotonic()
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    if on_process_started is not None:
        on_process_started(process)

    timed_out = False
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        timed_out = True
        stdout_bytes, stderr_bytes = await _terminate_and_drain(process)

    return ProcessResult(
        stdout=stdout_bytes.decode("utf-8", errors="replace"),
        stderr=stderr_bytes.decode("utf-8", errors="replace"),
        return_code=process.returncode,
        timed_out=timed_out,
        duration_seconds=time.monotonic() - started,
    )


async def terminate_process(process: asyncio.subprocess.Process) -> None:
    """Terminate ``process``, escalating to ``kill`` if it ignores the signal.

    Used both by :func:`run_subprocess`'s own timeout handling and by the
    execution engine's cancel/kill process control.
    """
    if process.returncode is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=_TERMINATE_GRACE_SECONDS)
    except asyncio.TimeoutError:
        logger.warning("Process %s ignored terminate(); killing.", process.pid)
        process.kill()
        await process.wait()


async def _terminate_and_drain(process: asyncio.subprocess.Process) -> tuple[bytes, bytes]:
    await terminate_process(process)
    try:
        return await asyncio.wait_for(process.communicate(), timeout=_TERMINATE_GRACE_SECONDS)
    except asyncio.TimeoutError:
        return b"", b""
