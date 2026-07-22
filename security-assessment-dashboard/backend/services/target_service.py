"""Service layer for target management within an assessment.

Owns everything the ``targets`` API routes need: CRUD, enable/disable,
duplication, bulk TXT/CSV import, export, and standalone validation.
Validation/normalization logic itself lives in
:mod:`backend.utils.target_validators`; this service is the transactional
and persistence layer around it.
"""

from __future__ import annotations

import csv
import io
import logging
import uuid
from urllib.parse import urlparse, urlunparse

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import ConflictError, InvalidInputError, NotFoundError
from backend.database.pagination import Page, Pagination, Sort, SortDirection
from backend.models.assessment import Assessment
from backend.models.enums import AssessmentHistoryEventType, TargetOrigin, TargetType
from backend.models.target import Target
from backend.schemas.target import (
    TargetBulkImportResult,
    TargetCreate,
    TargetImportError,
    TargetRead,
    TargetUpdate,
    TargetValidateRequest,
    TargetValidateResponse,
)
from backend.services.assessment_history_logger import log_assessment_event
from backend.utils.target_validators import TargetValidationError, detect_target_type, validate_target

logger = logging.getLogger(__name__)

_TARGET_SORT_FIELDS = {"target_type", "target_value", "enabled", "created_at", "updated_at"}
_HEADER_TOKENS = {"target_value", "value", "target"}
_TYPE_HEADER_TOKENS = {"target_type", "type"}


class TargetService:
    """Business logic for managing targets scoped to one assessment."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- Commands -----------------------------------------------------

    async def create(self, assessment_id: uuid.UUID, payload: TargetCreate) -> TargetRead:
        await self._ensure_assessment_exists(assessment_id)
        normalized_value = self._validate_value(payload.target_type, payload.target_value)
        await self._ensure_target_available(assessment_id, normalized_value)

        target = Target(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            target_type=payload.target_type,
            target_value=normalized_value,
            notes=payload.notes,
        )
        self._session.add(target)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"Target '{normalized_value}' already exists in this assessment.") from exc

        await log_assessment_event(
            self._session,
            assessment_id,
            AssessmentHistoryEventType.TARGET_ADDED,
            f"Target added: {normalized_value} ({payload.target_type.value}).",
        )
        return TargetRead.model_validate(target)

    async def update(self, assessment_id: uuid.UUID, target_id: uuid.UUID, payload: TargetUpdate) -> TargetRead:
        target = await self._get_target_or_404(assessment_id, target_id)

        effective_type = payload.target_type or target.target_type
        if payload.target_value is not None:
            normalized_value = self._validate_value(effective_type, payload.target_value)
        elif payload.target_type is not None and payload.target_type != target.target_type:
            # Type changed but value didn't — re-validate the existing value against the new type.
            normalized_value = self._validate_value(effective_type, target.target_value)
        else:
            normalized_value = target.target_value

        if normalized_value != target.target_value:
            await self._ensure_target_available(assessment_id, normalized_value, exclude_id=target.id)

        target.target_value = normalized_value
        target.target_type = effective_type
        if payload.notes is not None:
            target.notes = payload.notes
        if payload.enabled is not None:
            target.enabled = payload.enabled

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"Target '{normalized_value}' already exists in this assessment.") from exc

        await log_assessment_event(
            self._session, assessment_id, AssessmentHistoryEventType.TARGET_UPDATED, f"Target updated: {normalized_value}."
        )
        return TargetRead.model_validate(target)

    async def delete(self, assessment_id: uuid.UUID, target_id: uuid.UUID) -> None:
        target = await self._get_target_or_404(assessment_id, target_id)
        value = target.target_value
        await self._session.delete(target)
        await self._session.flush()
        await log_assessment_event(
            self._session, assessment_id, AssessmentHistoryEventType.TARGET_REMOVED, f"Target removed: {value}."
        )

    async def set_enabled(self, assessment_id: uuid.UUID, target_id: uuid.UUID, enabled: bool) -> TargetRead:
        target = await self._get_target_or_404(assessment_id, target_id)
        target.enabled = enabled
        await self._session.flush()
        return TargetRead.model_validate(target)

    async def duplicate(self, assessment_id: uuid.UUID, target_id: uuid.UUID, explicit_value: str | None) -> TargetRead:
        """Clone a target's type/notes/enabled state under a new, guaranteed-unique value.

        IPv4/IPv6/CIDR targets have no safe auto-generated "nearby" value —
        rather than fabricate one, ``explicit_value`` is required for them.
        """
        source = await self._get_target_or_404(assessment_id, target_id)

        if explicit_value:
            candidate = self._validate_value(source.target_type, explicit_value)
        else:
            candidate = self._auto_suffix_value(source.target_type, source.target_value)

        await self._ensure_target_available(assessment_id, candidate)

        clone = Target(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            target_type=source.target_type,
            target_value=candidate,
            notes=source.notes,
            enabled=source.enabled,
        )
        self._session.add(clone)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"Target '{candidate}' already exists in this assessment.") from exc

        await log_assessment_event(
            self._session,
            assessment_id,
            AssessmentHistoryEventType.TARGET_ADDED,
            f"Target duplicated from {source.target_value}: {candidate}.",
        )
        return TargetRead.model_validate(clone)

    async def bulk_import(self, assessment_id: uuid.UUID, filename: str, content: bytes) -> TargetBulkImportResult:
        """Import targets from an uploaded TXT (one value per line) or CSV
        (``target_type,target_value`` or a single value column) file.

        Invalid lines are skipped and reported; duplicates (against both
        existing targets and other rows in the same file) are skipped and
        counted, never erroring the whole import.
        """
        await self._ensure_assessment_exists(assessment_id)

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InvalidInputError("Import file must be UTF-8 encoded text.") from exc

        rows = self._parse_import_rows(text, is_csv=filename.lower().endswith(".csv"))
        existing_values = await self._existing_target_values(assessment_id)
        seen_in_batch: set[str] = set()

        imported: list[Target] = []
        errors: list[TargetImportError] = []
        skipped_duplicates = 0

        for line_number, (raw_type, raw_value) in enumerate(rows, start=1):
            if not raw_value.strip():
                continue

            target_type = self._resolve_import_type(raw_type)
            if target_type is None and raw_type:
                errors.append(
                    TargetImportError(line_number=line_number, raw_value=raw_value, reason=f"'{raw_type}' is not a recognized target type.")
                )
                continue
            if target_type is None:
                target_type = detect_target_type(raw_value)
            if target_type is None:
                errors.append(TargetImportError(line_number=line_number, raw_value=raw_value, reason="Could not determine target type."))
                continue

            try:
                normalized = validate_target(target_type, raw_value)
            except TargetValidationError as exc:
                errors.append(TargetImportError(line_number=line_number, raw_value=raw_value, reason=str(exc)))
                continue

            if normalized in existing_values or normalized in seen_in_batch:
                skipped_duplicates += 1
                continue

            seen_in_batch.add(normalized)
            target = Target(id=uuid.uuid4(), assessment_id=assessment_id, target_type=target_type, target_value=normalized)
            self._session.add(target)
            imported.append(target)

        if imported:
            await self._session.flush()
            await log_assessment_event(
                self._session,
                assessment_id,
                AssessmentHistoryEventType.TARGETS_IMPORTED,
                f"Imported {len(imported)} target(s) from '{filename}' "
                f"({len(errors)} invalid, {skipped_duplicates} duplicate, {len(rows)} line(s) total).",
            )

        return TargetBulkImportResult(
            total_lines=len(rows),
            imported=len(imported),
            skipped_duplicates=skipped_duplicates,
            skipped_invalid=len(errors),
            errors=errors,
            imported_targets=[TargetRead.model_validate(t) for t in imported],
        )

    # -- Queries --------------------------------------------------------

    async def get(self, assessment_id: uuid.UUID, target_id: uuid.UUID) -> TargetRead:
        target = await self._get_target_or_404(assessment_id, target_id)
        return TargetRead.model_validate(target)

    async def list(
        self,
        assessment_id: uuid.UUID,
        *,
        search: str | None = None,
        target_type_filter: TargetType | None = None,
        enabled_filter: bool | None = None,
        sort: Sort | None = None,
        pagination: Pagination | None = None,
    ) -> Page[TargetRead]:
        await self._ensure_assessment_exists(assessment_id)
        pagination = pagination or Pagination()
        sort = sort or Sort(field="created_at", direction=SortDirection.DESC)
        if sort.field not in _TARGET_SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort targets by '{sort.field}'.")

        # Pipeline-generated endpoint targets (e.g. 'http://host:80') are real Target rows but
        # deliberately excluded here -- this is the user-facing tab/picker, and cluttering it
        # with synthetic endpoints the Assessment Pipeline generated would defeat the point of
        # keeping them out of the way. They remain fully visible via the execution graph.
        conditions = [Target.assessment_id == assessment_id, Target.origin == TargetOrigin.USER]
        if search and search.strip():
            conditions.append(Target.target_value.ilike(f"%{search.strip()}%"))
        if target_type_filter is not None:
            conditions.append(Target.target_type == target_type_filter)
        if enabled_filter is not None:
            conditions.append(Target.enabled == enabled_filter)

        sort_column = getattr(Target, sort.field)
        order_by = sort_column.desc() if sort.direction == SortDirection.DESC else sort_column.asc()

        total = (await self._session.execute(select(func.count()).select_from(Target).where(*conditions))).scalar_one()
        stmt = select(Target).where(*conditions).order_by(order_by).offset(pagination.offset).limit(pagination.page_size)
        targets = list((await self._session.execute(stmt)).scalars().all())

        items = [TargetRead.model_validate(t) for t in targets]
        return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    async def list_all(
        self,
        *,
        assessment_id: uuid.UUID | None = None,
        search: str | None = None,
        target_type_filter: TargetType | None = None,
        enabled_filter: bool | None = None,
        sort: Sort | None = None,
        pagination: Pagination | None = None,
    ) -> Page[TargetRead]:
        """List targets workspace-wide (every assessment) or scoped to one, for the top-level Targets page.

        Distinct from :meth:`list`: that method is nested-under-one-assessment
        and 404s if the assessment doesn't exist; this one is the Target
        equivalent of ``HostInventoryQueryService.list_hosts``' optional
        ``assessment_id`` scope -- omitted, it reports across the whole
        workspace, matching how the Dashboard already frames itself.
        """
        pagination = pagination or Pagination()
        sort = sort or Sort(field="created_at", direction=SortDirection.DESC)
        if sort.field not in _TARGET_SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort targets by '{sort.field}'.")

        conditions = [Target.origin == TargetOrigin.USER]
        if assessment_id is not None:
            conditions.append(Target.assessment_id == assessment_id)
        if search and search.strip():
            conditions.append(Target.target_value.ilike(f"%{search.strip()}%"))
        if target_type_filter is not None:
            conditions.append(Target.target_type == target_type_filter)
        if enabled_filter is not None:
            conditions.append(Target.enabled == enabled_filter)

        sort_column = getattr(Target, sort.field)
        order_by = sort_column.desc() if sort.direction == SortDirection.DESC else sort_column.asc()

        total = (await self._session.execute(select(func.count()).select_from(Target).where(*conditions))).scalar_one()
        stmt = select(Target).where(*conditions).order_by(order_by).offset(pagination.offset).limit(pagination.page_size)
        targets = list((await self._session.execute(stmt)).scalars().all())

        items = [TargetRead.model_validate(t) for t in targets]
        return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    async def export(self, assessment_id: uuid.UUID, export_format: str) -> str:
        """Return every target in the assessment, serialized as TXT or CSV text."""
        await self._ensure_assessment_exists(assessment_id)
        stmt = select(Target).where(Target.assessment_id == assessment_id).order_by(Target.target_value.asc())
        targets = list((await self._session.execute(stmt)).scalars().all())

        if export_format == "csv":
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["target_type", "target_value", "enabled", "notes"])
            for target in targets:
                writer.writerow([target.target_type.value, target.target_value, target.enabled, target.notes or ""])
            return buffer.getvalue()

        return "\n".join(target.target_value for target in targets)

    @staticmethod
    def validate(payload: TargetValidateRequest) -> TargetValidateResponse:
        """Dry-run validation: check a value without saving anything."""
        try:
            normalized = validate_target(payload.target_type, payload.target_value)
        except TargetValidationError as exc:
            return TargetValidateResponse(valid=False, message=str(exc))
        return TargetValidateResponse(valid=True, normalized_value=normalized)

    # -- Internal helpers -------------------------------------------------

    @staticmethod
    def _validate_value(target_type: TargetType, raw_value: str) -> str:
        try:
            return validate_target(target_type, raw_value)
        except TargetValidationError as exc:
            raise InvalidInputError(str(exc)) from exc

    @staticmethod
    def _auto_suffix_value(target_type: TargetType, value: str) -> str:
        if target_type in (TargetType.IPV4, TargetType.IPV6, TargetType.CIDR):
            raise InvalidInputError(
                f"Cannot auto-duplicate a {target_type.value} target — supply an explicit target_value."
            )
        if target_type == TargetType.URL:
            parsed = urlparse(value)
            return urlunparse(parsed._replace(path=f"{parsed.path or '/'}-copy"))
        return f"copy-{value}"

    async def _ensure_assessment_exists(self, assessment_id: uuid.UUID) -> None:
        stmt = select(Assessment.id).where(Assessment.id == assessment_id, Assessment.deleted_at.is_(None))
        if (await self._session.execute(stmt)).scalar_one_or_none() is None:
            raise NotFoundError(f"Assessment {assessment_id} not found.")

    async def _get_target_or_404(self, assessment_id: uuid.UUID, target_id: uuid.UUID) -> Target:
        await self._ensure_assessment_exists(assessment_id)
        stmt = select(Target).where(Target.id == target_id, Target.assessment_id == assessment_id)
        target = (await self._session.execute(stmt)).scalar_one_or_none()
        if target is None:
            raise NotFoundError(f"Target {target_id} not found in assessment {assessment_id}.")
        return target

    async def _ensure_target_available(self, assessment_id: uuid.UUID, target_value: str, *, exclude_id: uuid.UUID | None = None) -> None:
        stmt = select(Target.id).where(Target.assessment_id == assessment_id, Target.target_value == target_value)
        if exclude_id is not None:
            stmt = stmt.where(Target.id != exclude_id)
        if (await self._session.execute(stmt)).scalar_one_or_none() is not None:
            raise ConflictError(f"Target '{target_value}' already exists in this assessment.")

    async def _existing_target_values(self, assessment_id: uuid.UUID) -> set[str]:
        stmt = select(Target.target_value).where(Target.assessment_id == assessment_id)
        return set((await self._session.execute(stmt)).scalars().all())

    @staticmethod
    def _resolve_import_type(raw_type: str | None) -> TargetType | None:
        if not raw_type or not raw_type.strip():
            return None
        try:
            return TargetType(raw_type.strip().lower())
        except ValueError:
            return None

    @staticmethod
    def _parse_import_rows(text: str, *, is_csv: bool) -> list[tuple[str | None, str]]:
        rows: list[tuple[str | None, str]] = []
        if is_csv:
            reader = csv.reader(io.StringIO(text))
            for row in reader:
                if not row:
                    continue
                if len(row) >= 2:
                    rows.append((row[0].strip(), row[1].strip()))
                else:
                    rows.append((None, row[0].strip()))
            if rows:
                first_type, first_value = rows[0]
                looks_like_header = first_value.lower() in _HEADER_TOKENS or (
                    first_type is not None and first_type.lower() in _TYPE_HEADER_TOKENS
                )
                if looks_like_header:
                    rows = rows[1:]
        else:
            for line in text.splitlines():
                stripped = line.strip()
                if stripped:
                    rows.append((None, stripped))
        return rows
