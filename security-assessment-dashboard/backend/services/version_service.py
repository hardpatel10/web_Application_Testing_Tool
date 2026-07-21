"""Service layer for application version and build information."""

import platform
import subprocess
from pathlib import Path

from backend.core.config import Settings
from backend.schemas.version import VersionResponse


class VersionService:
    """Resolves application version, build identifier, and runtime version."""

    def __init__(self, settings: Settings, project_root: Path) -> None:
        self._settings = settings
        self._project_root = project_root

    def _resolve_build_id(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return "unknown"

        if result.returncode != 0:
            return "unknown"

        return result.stdout.strip() or "unknown"

    def get_version(self) -> VersionResponse:
        return VersionResponse(
            version=self._settings.app_version,
            build=self._resolve_build_id(),
            python_version=platform.python_version(),
        )
