"""Filesystem layout helpers for per-assessment data directories.

Every assessment gets a fixed set of subdirectories under the configured
assessment root (``Settings.assessment_root_dir``), created eagerly when
the assessment is created so later phases (tool execution, parsing,
reporting) can assume they already exist without each needing its own
directory-creation logic.
"""

import uuid
from pathlib import Path

ASSESSMENT_SUBDIRECTORIES: tuple[str, ...] = (
    "raw",
    "parsed",
    "reports",
    "screenshots",
    "logs",
    "exports",
    "attachments",
)


def assessment_directory(assessment_root: Path, assessment_id: uuid.UUID) -> Path:
    """Return the root directory for one assessment's on-disk data."""
    return assessment_root / str(assessment_id)


def create_assessment_directories(assessment_root: Path, assessment_id: uuid.UUID) -> Path:
    """Create (if missing) an assessment's root directory and all standard subdirectories.

    Idempotent — safe to call again (e.g. when duplicating an assessment)
    without error.
    """
    root = assessment_directory(assessment_root, assessment_id)
    for subdirectory in ASSESSMENT_SUBDIRECTORIES:
        (root / subdirectory).mkdir(parents=True, exist_ok=True)
    return root
