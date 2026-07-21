"""Request/response schemas for targets."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.enums import TargetType


class TargetCreate(BaseModel):
    """Payload to add a target to an assessment."""

    target_type: TargetType
    target_value: str = Field(min_length=1, max_length=512)
    notes: str | None = None


class TargetUpdate(BaseModel):
    """Payload to partially update a target. Omitted fields are left unchanged."""

    target_type: TargetType | None = None
    target_value: str | None = Field(default=None, min_length=1, max_length=512)
    notes: str | None = None
    enabled: bool | None = None


class TargetRead(BaseModel):
    """A target as returned by the API."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    assessment_id: uuid.UUID
    target_type: TargetType
    target_value: str
    resolved_ip: str | None
    notes: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class TargetDuplicateRequest(BaseModel):
    """Optional explicit value for a duplicated target.

    IPv4/IPv6/CIDR targets have no safe auto-generated variant (the service
    refuses to fabricate a nearby-but-different address), so ``target_value``
    is required for those types and optional for hostname/domain/URL, where
    the service can auto-suffix a value to keep it unique.
    """

    target_value: str | None = Field(default=None, max_length=512)


class TargetValidateRequest(BaseModel):
    """A target value to check without saving it."""

    target_type: TargetType
    target_value: str = Field(min_length=1, max_length=512)


class TargetValidateResponse(BaseModel):
    """Result of a dry-run target validation."""

    valid: bool
    normalized_value: str | None = None
    message: str | None = None


class TargetImportError(BaseModel):
    """One rejected line from a bulk import."""

    line_number: int
    raw_value: str
    reason: str


class TargetBulkImportResult(BaseModel):
    """Summary of a bulk target import."""

    total_lines: int
    imported: int
    skipped_duplicates: int
    skipped_invalid: int
    errors: list[TargetImportError]
    imported_targets: list[TargetRead]
