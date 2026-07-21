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
"""

import logging
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_VERSION_TIMEOUT_SECONDS = 5.0


def default_search_directories() -> list[Path]:
    """Common installation directories to check beyond ``PATH``, existing ones only."""
    home = Path.home()
    if platform.system() == "Windows":
        candidates = [
            home / "go" / "bin",  # `go install` default — most ProjectDiscovery tools
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
            Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "chocolatey" / "bin",
            home / "scoop" / "shims",
            home / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links",
        ]
    else:
        candidates = [
            home / "go" / "bin",
            home / ".local" / "bin",
            Path("/usr/local/bin"),
            Path("/usr/local/sbin"),
            Path("/usr/bin"),
            Path("/usr/sbin"),
            Path("/opt"),
            Path("/snap/bin"),
        ]
    return [directory for directory in candidates if directory.is_dir()]


def find_executable(
    binary_names: list[str],
    *,
    custom_path: Path | None = None,
    extra_search_dirs: list[Path] | None = None,
) -> Path | None:
    """Locate one of ``binary_names`` on this machine.

    Search order: an explicit ``custom_path`` override (used as-is if valid,
    never falls through to auto-discovery), then ``PATH`` (``shutil.which``),
    then common installation directories.
    """
    if custom_path is not None:
        return custom_path if custom_path.is_file() and os.access(custom_path, os.X_OK) else None

    for name in binary_names:
        found = shutil.which(name)
        if found:
            return Path(found)

    windows_suffix = ".exe" if platform.system() == "Windows" else ""
    for directory in extra_search_dirs if extra_search_dirs is not None else default_search_directories():
        for name in binary_names:
            candidate = directory / f"{name}{windows_suffix}"
            if candidate.is_file():
                return candidate
    return None


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
