"""Request/response schemas for assessments."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from backend.models.enums import AssessmentHistoryEventType, AssessmentStatus, AssessmentType

_TAG_MAX_LENGTH = 64


def _normalize_tags(tags: list[str]) -> list[str]:
    """Trim, lowercase, drop blanks, and de-duplicate a tag list, preserving order."""
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        cleaned = tag.strip().lower()
        if not cleaned:
            continue
        if len(cleaned) > _TAG_MAX_LENGTH:
            raise ValueError(f"Tag '{cleaned}' exceeds {_TAG_MAX_LENGTH} characters.")
        if cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return normalized


class AssessmentCreate(BaseModel):
    """Payload to create a new assessment."""

    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: str | None = None
    assessment_type: AssessmentType
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Name must not be blank.")
        return trimmed

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, value: list[str]) -> list[str]:
        return _normalize_tags(value)


class AssessmentUpdate(BaseModel):
    """Payload to partially update an assessment. Omitted fields are left unchanged."""

    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: str | None = None
    assessment_type: AssessmentType | None = None
    status: AssessmentStatus | None = None
    tags: list[str] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def _trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Name must not be blank.")
        return trimmed

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_tags(value)


class AssessmentRead(BaseModel):
    """An assessment as returned by the API.

    Built explicitly by the service layer (not via ``model_validate`` on
    the bare ORM instance) because ``tags`` and ``target_count`` are
    derived — the former from the ``AssessmentTag`` relationship, the
    latter from a count query — rather than plain columns.
    """

    id: uuid.UUID
    name: str
    description: str | None
    assessment_type: AssessmentType
    status: AssessmentStatus
    tags: list[str]
    target_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssessmentHistoryEntryRead(BaseModel):
    """One entry in an assessment's activity log."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    event_type: AssessmentHistoryEventType
    message: str
    created_at: datetime


class AssessmentDuplicateRequest(BaseModel):
    """Optional override for a duplicated assessment's name.

    If omitted, the service generates one (source name + " (Copy)",
    disambiguated further if that name is also taken).
    """

    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
