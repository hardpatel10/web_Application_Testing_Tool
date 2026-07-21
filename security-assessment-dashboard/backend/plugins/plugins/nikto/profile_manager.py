"""Loads, validates, searches, and persists Nikto Scan Profiles.

Profiles are DATA (JSON files), never code. Built-in profiles ship
read-only alongside this plugin (``profiles/`` under the plugin's own
directory); custom, user-created profiles live in a separate, writable
directory (``data/profiles/nikto/`` by default) so a plugin reinstall or
upgrade never touches user data, and a built-in profile can never be
edited or deleted in place — only duplicated into an editable custom one.

Structurally identical to ``backend.plugins.plugins.nmap.profile_manager``
(same file-per-profile-id JSON storage, same built-in/custom precedence,
same CRUD contract) — kept as a separate class per plugin (not a shared
base class) because each plugin's ``ScanProfile``/``ProfileCategory``/
``RiskLevel`` types are deliberately distinct Pydantic models with
different fields, and this manager validates against its own plugin's
types only, for the same synthetic-module-identity reason documented
below.

Has no database or HTTP dependency (pure filesystem + Pydantic), per
``.claude/CLAUDE.md``'s plugin philosophy — ``backend.services.scan_profile_service``
is what a route handler actually calls, and it is the layer that translates
these exceptions into HTTP-aware ones.
"""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from backend.plugins.exceptions import PluginNotFoundError, PluginValidationError

from .models import ProfileCategory, RiskLevel, ScanProfile

logger = logging.getLogger(__name__)


class ProfileNotFoundError(PluginNotFoundError):
    """Raised when a profile id doesn't match any loaded profile.

    Inherits from the plugin framework's stable ``PluginNotFoundError``
    (imported the same, ordinary way everywhere) rather than being a bare
    ``Exception`` -- this plugin's own directory is loaded as a synthetic
    package with a fresh module identity per load (see the Phase 4 loader),
    so an ``except ProfileNotFoundError`` written in code that imported
    this class via the plugin's *normal* dotted path (as
    ``backend.services.scan_profile_service`` must, since it isn't
    plugin-internal code) would never match an instance actually raised
    from inside the synthetically-loaded module.
    """


class ProfileValidationError(PluginValidationError):
    """Raised for invalid profile data or an operation a built-in profile forbids. See :class:`ProfileNotFoundError`."""


class ProfileManager:
    """Read-only access to built-in profiles; full CRUD over custom ones."""

    def __init__(self, built_in_dir: Path, custom_dir: Path) -> None:
        self._built_in_dir = built_in_dir
        self._custom_dir = custom_dir
        self._custom_dir.mkdir(parents=True, exist_ok=True)

    # -- Queries --------------------------------------------------------------

    def list_profiles(self) -> list[ScanProfile]:
        """Every valid profile, built-in first, then custom. A custom id colliding with a built-in one is skipped."""
        by_id: dict[str, ScanProfile] = {}
        for path in sorted(self._built_in_dir.glob("*.json")):
            profile = self._load_file(path, built_in=True)
            if profile is not None:
                by_id[profile.id] = profile
        for path in sorted(self._custom_dir.glob("*.json")):
            profile = self._load_file(path, built_in=False)
            if profile is not None and profile.id not in by_id:
                by_id[profile.id] = profile
        return list(by_id.values())

    def get(self, profile_id: str) -> ScanProfile:
        for profile in self.list_profiles():
            if profile.id == profile_id:
                return profile
        raise ProfileNotFoundError(f"Scan profile '{profile_id}' not found.")

    def search(
        self, *, query: str | None = None, category: ProfileCategory | None = None, risk_level: RiskLevel | None = None
    ) -> list[ScanProfile]:
        results = self.list_profiles()
        if category is not None:
            results = [profile for profile in results if profile.category == category]
        if risk_level is not None:
            results = [profile for profile in results if profile.risk_level == risk_level]
        if query and query.strip():
            term = query.strip().lower()
            results = [profile for profile in results if term in profile.name.lower() or term in profile.description.lower()]
        return results

    # -- Custom profile CRUD ----------------------------------------------------

    def create_custom(self, data: dict) -> ScanProfile:
        """Validate and persist a new custom profile. Takes a plain ``dict``, not a pre-built ``ScanProfile``."""
        profile = self._validate(data, built_in=False)
        if any(existing.id == profile.id for existing in self.list_profiles()):
            raise ProfileValidationError(f"A profile with id '{profile.id}' already exists.")
        self._write(profile)
        return profile

    def update_custom(self, profile_id: str, data: dict) -> ScanProfile:
        existing = self.get(profile_id)
        if existing.built_in:
            raise ProfileValidationError(f"'{profile_id}' is a built-in profile and cannot be edited. Duplicate it first.")
        profile = self._validate(data, built_in=False)
        if profile.id != profile_id and any(other.id == profile.id for other in self.list_profiles()):
            raise ProfileValidationError(f"A profile with id '{profile.id}' already exists.")
        self._write(profile)
        if profile.id != profile_id:
            self._delete_file(profile_id)
        return profile

    def delete_custom(self, profile_id: str) -> None:
        existing = self.get(profile_id)
        if existing.built_in:
            raise ProfileValidationError(f"'{profile_id}' is a built-in profile and cannot be deleted.")
        self._delete_file(profile_id)

    def duplicate(self, profile_id: str, new_id: str, new_name: str | None = None) -> ScanProfile:
        source = self.get(profile_id)
        if any(existing.id == new_id for existing in self.list_profiles()):
            raise ProfileValidationError(f"A profile with id '{new_id}' already exists.")
        copy = source.model_copy(update={"id": new_id, "name": new_name or f"{source.name} (Copy)", "built_in": False})
        self._write(copy)
        return copy

    # -- Import / export -------------------------------------------------------

    def import_profile(self, data: dict) -> ScanProfile:
        return self.create_custom(data)

    def export_profile(self, profile_id: str) -> dict:
        return self.get(profile_id).model_dump(exclude={"built_in"}, mode="json")

    # -- Internal helpers -------------------------------------------------------

    @staticmethod
    def _validate(data: dict, *, built_in: bool) -> ScanProfile:
        try:
            return ScanProfile.model_validate({**data, "built_in": built_in})
        except ValidationError as exc:
            raise ProfileValidationError(f"Invalid profile data: {exc}") from exc

    @classmethod
    def _load_file(cls, path: Path, *, built_in: bool) -> ScanProfile | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Skipping unreadable profile file '%s': %s", path, exc)
            return None
        try:
            return cls._validate(data, built_in=built_in)
        except ProfileValidationError as exc:
            logger.warning("Skipping invalid profile file '%s': %s", path, exc)
            return None

    def _write(self, profile: ScanProfile) -> None:
        path = self._custom_dir / f"{profile.id}.json"
        payload = profile.model_dump(exclude={"built_in"}, mode="json")
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _delete_file(self, profile_id: str) -> None:
        path = self._custom_dir / f"{profile_id}.json"
        if path.is_file():
            path.unlink()
