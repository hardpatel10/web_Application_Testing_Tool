"""Shared installation-detection helpers for tool plugins.

Every real tool plugin's ``check_installation()``/``get_version()``
delegate to these functions instead of reimplementing PATH search and
subprocess handling 15 times. ``run_version_command`` is the *only*
subprocess call any of these plugins make, and it only ever invokes a
version flag (``--version``, ``-version``, ...) — never a target, never a
scan. That is a detection mechanism the phase brief explicitly requires
("Automatically retrieve the real version... Never hardcode versions."),
not the tool execution this phase forbids: it takes no target argument
and never touches the network.

The runtime target for this application is Linux only (development
happens on Windows, but nothing here needs to run there) — see
``.claude/CLAUDE.md``. Detection therefore only ever looks at POSIX
conventions (``PATH`` / ``which``, and common Linux install directories).
"""

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_VERSION_TIMEOUT_SECONDS = 5.0

#: Detection method labels returned by :func:`resolve_executable_detailed`, surfaced verbatim
#: in Tool Management's Diagnostics tab so a user can see *how* (not just whether) a tool was found.
DETECTION_METHOD_CUSTOM_PATH = "custom_path"
DETECTION_METHOD_PATH = "path"
DETECTION_METHOD_SEARCH_DIRECTORY = "search_directory"
DETECTION_METHOD_NOT_FOUND = "not_found"


def default_search_directories() -> list[Path]:
    """Common Linux installation directories to check beyond ``PATH``, existing ones only."""
    home = Path.home()
    candidates = [
        home / "go" / "bin",  # `go install` default — most ProjectDiscovery tools
        home / ".local" / "bin",
        Path("/usr/local/bin"),
        Path("/usr/local/sbin"),
        Path("/usr/bin"),
        Path("/usr/sbin"),
        Path("/opt"),
        Path("/snap/bin"),
    ]
    return [directory for directory in candidates if directory.is_dir()]


def resolve_executable_detailed(
    binary_names: list[str],
    *,
    custom_path: Path | None = None,
    extra_search_dirs: list[Path] | None = None,
) -> tuple[Path | None, str]:
    """Locate one of ``binary_names`` on this machine, reporting *how* it was found.

    Search order: an explicit ``custom_path`` override (used as-is if valid,
    never falls through to auto-discovery), then ``PATH`` (``shutil.which``),
    then common Linux installation directories. The returned method string is
    one of the ``DETECTION_METHOD_*`` constants above.
    """
    if custom_path is not None:
        found = custom_path.is_file() and os.access(custom_path, os.X_OK)
        return (custom_path, DETECTION_METHOD_CUSTOM_PATH) if found else (None, DETECTION_METHOD_CUSTOM_PATH)

    for name in binary_names:
        found = shutil.which(name)
        if found:
            return Path(found), DETECTION_METHOD_PATH

    for directory in extra_search_dirs if extra_search_dirs is not None else default_search_directories():
        for name in binary_names:
            candidate = directory / name
            if candidate.is_file():
                return candidate, DETECTION_METHOD_SEARCH_DIRECTORY
    return None, DETECTION_METHOD_NOT_FOUND


def find_executable(
    binary_names: list[str],
    *,
    custom_path: Path | None = None,
    extra_search_dirs: list[Path] | None = None,
) -> Path | None:
    """Locate one of ``binary_names`` on this machine. See :func:`resolve_executable_detailed` for detail."""
    executable, _method = resolve_executable_detailed(
        binary_names, custom_path=custom_path, extra_search_dirs=extra_search_dirs
    )
    return executable


def validate_custom_executable(custom_path: Path, expected_binary_names: list[str]) -> list[str]:
    """Validate a user-specified executable override. Returns a list of error messages (empty if valid)."""
    if not custom_path.exists():
        return [f"'{custom_path}' does not exist."]
    if not custom_path.is_file():
        return [f"'{custom_path}' is not a file."]

    errors = []
    if not os.access(custom_path, os.X_OK):
        errors.append(f"'{custom_path}' is not executable.")

    stem = custom_path.stem.lower()
    if not any(stem == name.lower() for name in expected_binary_names):
        errors.append(
            f"'{custom_path.name}' does not match the expected binary name(s): {', '.join(expected_binary_names)}."
        )
    return errors


def run_version_command(
    executable: Path, args: list[str], *, timeout: float = _DEFAULT_VERSION_TIMEOUT_SECONDS
) -> tuple[str, str, int | None]:
    """Run ``executable`` with a version flag ONLY. Never used for scanning.

    Returns ``(stdout, stderr, return_code)`` — ``return_code`` is ``None``
    if the process could not be started or timed out.
    """
    try:
        result = subprocess.run(  # noqa: S603 - fixed version-flag args only, no shell, no target/user input
            [str(executable), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        logger.warning("Version check for '%s' timed out after %.1fs.", executable, timeout)
        return "", "Version check timed out.", None
    except OSError as exc:
        logger.warning("Version check for '%s' failed to start: %s", executable, exc)
        return "", str(exc), None


def extract_version(text: str, pattern: str) -> str | None:
    """Extract a version string from ``text`` using ``pattern`` (one capture group)."""
    match = re.search(pattern, text)
    return match.group(1) if match else None


#: Version-flag conventions to try, in order, when a plugin's own preferred flag yields nothing
#: usable. Different tools spell "show me your version" differently -- this is what "tolerant"
#: version detection means: try the common spellings rather than hardcoding exactly one.
_FALLBACK_VERSION_ARGS: tuple[tuple[str, ...], ...] = (
    ("--version",),
    ("-version",),
    ("version",),
    ("-v",),
    ("-V",),
)

#: Generic fallback pattern used when a plugin's own ``VERSION_PATTERN`` doesn't match the actual
#: output (e.g. the tool changed its banner format). Matches a dotted version number, optionally
#: prefixed with 'v' and optionally suffixed with a pre-release tag (e.g. "v2.5.0", "1.2", "3.0.1-beta").
_GENERIC_VERSION_PATTERN = r"\bv?(\d+\.\d+(?:\.\d+){0,2}(?:-[0-9A-Za-z.]+)?)\b"


@dataclass(frozen=True)
class VersionDetectionResult:
    """Outcome of trying to determine one tool's version, for both ``get_version()`` and diagnostics."""

    version: str | None
    command: list[str] | None
    raw_output: str


def detect_version(
    executable: Path,
    *,
    preferred_args: list[str] | None = None,
    pattern: str | None = None,
    timeout: float = _DEFAULT_VERSION_TIMEOUT_SECONDS,
) -> VersionDetectionResult:
    """Determine ``executable``'s version, tolerating unfamiliar flag/output conventions.

    Tries ``preferred_args`` first (a plugin's own best guess), then falls
    back through ``_FALLBACK_VERSION_ARGS``. For each attempt, first tries
    the plugin-specific ``pattern`` (if given), then a generic dotted-version
    pattern -- so a plugin author's regex doesn't have to be perfect for
    detection to still work, and a tool that changes its banner format
    doesn't silently go from "healthy" to "degraded".
    """
    candidates: list[tuple[str, ...]] = []
    if preferred_args:
        candidates.append(tuple(preferred_args))
    for args in _FALLBACK_VERSION_ARGS:
        if args not in candidates:
            candidates.append(args)

    for args in candidates:
        stdout, stderr, _return_code = run_version_command(executable, list(args), timeout=timeout)
        combined = f"{stdout}\n{stderr}".strip()
        if not combined:
            continue

        version = extract_version(combined, pattern) if pattern else None
        if version is None:
            version = extract_version(combined, _GENERIC_VERSION_PATTERN)
        if version:
            return VersionDetectionResult(version=version, command=list(args), raw_output=combined)

    return VersionDetectionResult(version=None, command=list(candidates[0]) if candidates else None, raw_output="")


def parse_version_tuple(version: str) -> tuple[int, ...]:
    """Parse a version string's leading numeric groups into a comparable tuple.

    Ignores any non-numeric pre-release/build suffix (e.g. ``"2.5.0-beta"`` -> ``(2, 5, 0)``).
    Non-numeric or empty input parses to an empty tuple, which compares as
    "older than everything" -- callers should already have confirmed the
    string looks version-like before relying on that.
    """
    match = re.match(r"(\d+(?:\.\d+)*)", version.strip())
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def is_version_at_least(detected: str, minimum: str) -> bool:
    """Return whether ``detected`` is >= ``minimum`` (dotted numeric version comparison)."""
    return parse_version_tuple(detected) >= parse_version_tuple(minimum)
