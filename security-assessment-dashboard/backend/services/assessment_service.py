"""Service layer for assessment management.

Owns everything the ``assessments`` API routes need: CRUD, archive/restore,
duplication, activity history, and search/sort/filter/pagination. Routes
stay thin and call straight into this layer; this layer is the only place
that touches both the ORM and the filesystem (per-assessment directories).
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.config import Settings
from backend.core.exceptions import ConflictError, InvalidInputError, NotFoundError
from backend.core.paths import create_assessment_directories
from backend.database.pagination import Page, Pagination, Sort, SortDirection
from backend.models.assessment import Assessment
from backend.models.assessment_history import AssessmentHistoryEntry
from backend.models.assessment_tag import AssessmentTag
from backend.models.base import utcnow
from backend.models.enums import AssessmentHistoryEventType, AssessmentStatus, AssessmentType, TargetOrigin
from backend.models.target import Target
from backend.schemas.assessment import (
    AssessmentCreate,
    AssessmentDuplicateRequest,
    AssessmentHistoryEntryRead,
    AssessmentRead,
    AssessmentUpdate,
)
from backend.services.assessment_history_logger import log_assessment_event

logger = logging.getLogger(__name__)

_ASSESSMENT_SORT_FIELDS = {"name", "status", "assessment_type", "started_at", "completed_at", "created_at", "updated_at"}


class AssessmentService:
    """Business logic for creating, querying, and managing assessments."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    # -- Commands -----------------------------------------------------

    async def create(self, payload: AssessmentCreate) -> AssessmentRead:
        """Create a new assessment, its tags, and its on-disk directory tree."""
        await self._ensure_name_available(payload.name)

        assessment_id = uuid.uuid4()
        assessment = Assessment(
            id=assessment_id,
            name=payload.name,
            description=payload.description,
            assessment_type=payload.assessment_type,
            status=AssessmentStatus.DRAFT,
        )
        self._session.add(assessment)
        for tag in payload.tags:
            self._session.add(AssessmentTag(assessment_id=assessment_id, tag=tag))

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"An assessment named '{payload.name}' already exists.") from exc

        create_assessment_directories(self._settings.assessment_root_dir, assessment_id)

        await log_assessment_event(
            self._session, assessment_id, AssessmentHistoryEventType.CREATED, f"Assessment '{payload.name}' created."
        )
        logger.info("Assessment created", extra={"extra_fields": {"assessment_id": str(assessment_id), "name": payload.name}})
        return await self._read(assessment_id)

    async def update(self, assessment_id: uuid.UUID, payload: AssessmentUpdate) -> AssessmentRead:
        """Partially update an assessment. Status transitions to/from ARCHIVED are rejected here."""
        assessment = await self._get_active_or_404(assessment_id)

        if payload.status == AssessmentStatus.ARCHIVED:
            raise InvalidInputError("Use the archive endpoint to archive an assessment.")
        if assessment.status == AssessmentStatus.ARCHIVED and payload.status not in (None, AssessmentStatus.ARCHIVED):
            raise InvalidInputError("Use the restore endpoint to bring an archived assessment out of ARCHIVED.")

        changed_fields: list[str] = []

        if payload.name is not None and payload.name != assessment.name:
            await self._ensure_name_available(payload.name, exclude_id=assessment.id)
            assessment.name = payload.name
            changed_fields.append("name")
        if payload.description is not None and payload.description != assessment.description:
            assessment.description = payload.description
            changed_fields.append("description")
        if payload.assessment_type is not None and payload.assessment_type != assessment.assessment_type:
            assessment.assessment_type = payload.assessment_type
            changed_fields.append("assessment_type")
        if payload.started_at is not None and payload.started_at != assessment.started_at:
            assessment.started_at = payload.started_at
            changed_fields.append("started_at")
        if payload.completed_at is not None and payload.completed_at != assessment.completed_at:
            assessment.completed_at = payload.completed_at
            changed_fields.append("completed_at")
        if payload.tags is not None:
            await self._replace_tags(assessment.id, payload.tags)
            changed_fields.append("tags")

        status_changed_to: AssessmentStatus | None = None
        if payload.status is not None and payload.status != assessment.status:
            assessment.status = payload.status
            status_changed_to = payload.status

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"An assessment named '{payload.name}' already exists.") from exc

        if changed_fields:
            await log_assessment_event(
                self._session,
                assessment.id,
                AssessmentHistoryEventType.UPDATED,
                f"Updated: {', '.join(changed_fields)}.",
            )
        if status_changed_to is not None:
            await log_assessment_event(
                self._session,
                assessment.id,
                AssessmentHistoryEventType.STATUS_CHANGED,
                f"Status changed to {status_changed_to.value}.",
            )

        return await self._read(assessment.id)

    async def delete(self, assessment_id: uuid.UUID) -> None:
        """Soft-delete an assessment: marks it deleted and hides it from listings.

        Never removes the database row or any on-disk file — per project
        requirements, cleanup of deleted assessments' data is explicitly
        deferred to a later phase.
        """
        assessment = await self._get_active_or_404(assessment_id)
        assessment.deleted_at = utcnow()
        await log_assessment_event(
            self._session,
            assessment.id,
            AssessmentHistoryEventType.DELETED,
            "Assessment deleted (on-disk data preserved).",
        )
        await self._session.flush()
        logger.info("Assessment soft-deleted", extra={"extra_fields": {"assessment_id": str(assessment_id)}})

    async def archive(self, assessment_id: uuid.UUID) -> AssessmentRead:
        """Move an assessment into the ARCHIVED status, remembering its prior status for restore."""
        assessment = await self._get_active_or_404(assessment_id)
        if assessment.status == AssessmentStatus.ARCHIVED:
            raise ConflictError("Assessment is already archived.")

        previous = assessment.status
        assessment.previous_status = previous
        assessment.status = AssessmentStatus.ARCHIVED
        await self._session.flush()

        await log_assessment_event(
            self._session,
            assessment.id,
            AssessmentHistoryEventType.ARCHIVED,
            f"Archived (was {previous.value}).",
        )
        return await self._read(assessment.id)

    async def restore(self, assessment_id: uuid.UUID) -> AssessmentRead:
        """Restore an archived assessment to the status it had before archiving."""
        assessment = await self._get_active_or_404(assessment_id)
        if assessment.status != AssessmentStatus.ARCHIVED:
            raise ConflictError("Assessment is not archived.")

        restored_status = assessment.previous_status or AssessmentStatus.READY
        assessment.status = restored_status
        assessment.previous_status = None
        await self._session.flush()

        await log_assessment_event(
            self._session,
            assessment.id,
            AssessmentHistoryEventType.RESTORED,
            f"Restored to {restored_status.value}.",
        )
        return await self._read(assessment.id)

    async def duplicate(self, assessment_id: uuid.UUID, payload: AssessmentDuplicateRequest) -> AssessmentRead:
        """Clone an assessment's metadata, tags, and targets into a new DRAFT assessment."""
        source = await self._get_active_or_404(assessment_id)
        new_name = payload.name.strip() if payload.name else await self._generate_copy_name(source.name)
        await self._ensure_name_available(new_name)

        source_targets_stmt = select(Target).where(Target.assessment_id == source.id)
        source_targets = list((await self._session.execute(source_targets_stmt)).scalars().all())

        new_id = uuid.uuid4()
        clone = Assessment(
            id=new_id,
            name=new_name,
            description=source.description,
            assessment_type=source.assessment_type,
            status=AssessmentStatus.DRAFT,
        )
        self._session.add(clone)
        for tag in source.tags:
            self._session.add(AssessmentTag(assessment_id=new_id, tag=tag.tag))
        for target in source_targets:
            self._session.add(
                Target(
                    id=uuid.uuid4(),
                    assessment_id=new_id,
                    target_type=target.target_type,
                    target_value=target.target_value,
                    resolved_ip=target.resolved_ip,
                    notes=target.notes,
                    enabled=target.enabled,
                )
            )

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"An assessment named '{new_name}' already exists.") from exc

        create_assessment_directories(self._settings.assessment_root_dir, new_id)

        await log_assessment_event(
            self._session,
            new_id,
            AssessmentHistoryEventType.DUPLICATED,
            f"Duplicated from '{source.name}' ({source.id}), including {len(source_targets)} target(s).",
        )
        await log_assessment_event(
            self._session,
            source.id,
            AssessmentHistoryEventType.DUPLICATED,
            f"Duplicated as '{new_name}' ({new_id}).",
        )
        return await self._read(new_id)

    # -- Queries --------------------------------------------------------

    async def get(self, assessment_id: uuid.UUID) -> AssessmentRead:
        return await self._read(assessment_id)

    async def list(
        self,
        *,
        search: str | None = None,
        status_filter: AssessmentStatus | None = None,
        assessment_type_filter: AssessmentType | None = None,
        tags_filter: list[str] | None = None,
        sort: Sort | None = None,
        pagination: Pagination | None = None,
    ) -> Page[AssessmentRead]:
        """Search, filter, sort, and paginate assessments (soft-deleted ones excluded)."""
        pagination = pagination or Pagination()
        sort = sort or Sort(field="created_at", direction=SortDirection.DESC)
        if sort.field not in _ASSESSMENT_SORT_FIELDS:
            raise InvalidInputError(f"Cannot sort assessments by '{sort.field}'.")

        conditions = [Assessment.deleted_at.is_(None)]
        if search and search.strip():
            like = f"%{search.strip()}%"
            conditions.append(or_(Assessment.name.ilike(like), Assessment.description.ilike(like)))
        if status_filter is not None:
            conditions.append(Assessment.status == status_filter)
        if assessment_type_filter is not None:
            conditions.append(Assessment.assessment_type == assessment_type_filter)
        if tags_filter:
            normalized = [t.strip().lower() for t in tags_filter if t.strip()]
            if normalized:
                conditions.append(
                    Assessment.id.in_(select(AssessmentTag.assessment_id).where(AssessmentTag.tag.in_(normalized)))
                )

        sort_column = getattr(Assessment, sort.field)
        order_by = sort_column.desc() if sort.direction == SortDirection.DESC else sort_column.asc()

        total = (await self._session.execute(select(func.count()).select_from(Assessment).where(*conditions))).scalar_one()

        stmt = (
            select(Assessment)
            .options(selectinload(Assessment.tags))
            .where(*conditions)
            .order_by(order_by)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        assessments = list((await self._session.execute(stmt)).scalars().all())
        counts = await self._count_targets_bulk([a.id for a in assessments])

        items = [self._to_schema(a, counts.get(a.id, 0)) for a in assessments]
        return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    async def get_history(self, assessment_id: uuid.UUID, pagination: Pagination | None = None) -> Page[AssessmentHistoryEntryRead]:
        """Return an assessment's activity log, newest first."""
        await self._get_active_or_404(assessment_id)
        pagination = pagination or Pagination(page_size=50)

        total = (
            await self._session.execute(
                select(func.count()).select_from(AssessmentHistoryEntry).where(AssessmentHistoryEntry.assessment_id == assessment_id)
            )
        ).scalar_one()

        stmt = (
            select(AssessmentHistoryEntry)
            .where(AssessmentHistoryEntry.assessment_id == assessment_id)
            .order_by(AssessmentHistoryEntry.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        entries = list((await self._session.execute(stmt)).scalars().all())
        items = [AssessmentHistoryEntryRead.model_validate(entry) for entry in entries]
        return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    # -- Internal helpers -------------------------------------------------

    async def _get_active_or_404(self, assessment_id: uuid.UUID) -> Assessment:
        stmt = (
            select(Assessment)
            .options(selectinload(Assessment.tags))
            .where(Assessment.id == assessment_id, Assessment.deleted_at.is_(None))
        )
        assessment = (await self._session.execute(stmt)).scalar_one_or_none()
        if assessment is None:
            raise NotFoundError(f"Assessment {assessment_id} not found.")
        return assessment

    async def _read(self, assessment_id: uuid.UUID) -> AssessmentRead:
        assessment = await self._get_active_or_404(assessment_id)
        # Counts only user-added targets -- consistent with the Targets tab's own list, which
        # excludes the Assessment Pipeline's synthetic endpoint targets (e.g. 'http://host:80')
        # from the user-facing scope. A pipeline run against one target could otherwise inflate
        # this count well past what the user themselves actually added.
        target_count = (
            await self._session.execute(
                select(func.count())
                .select_from(Target)
                .where(Target.assessment_id == assessment_id, Target.origin == TargetOrigin.USER)
            )
        ).scalar_one()
        return self._to_schema(assessment, target_count)

    async def _count_targets_bulk(self, assessment_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not assessment_ids:
            return {}
        stmt = (
            select(Target.assessment_id, func.count(Target.id))
            .where(Target.assessment_id.in_(assessment_ids), Target.origin == TargetOrigin.USER)
            .group_by(Target.assessment_id)
        )
        result = await self._session.execute(stmt)
        return dict(result.all())

    async def _ensure_name_available(self, name: str, *, exclude_id: uuid.UUID | None = None) -> None:
        stmt = select(Assessment.id).where(Assessment.name == name, Assessment.deleted_at.is_(None))
        if exclude_id is not None:
            stmt = stmt.where(Assessment.id != exclude_id)
        if (await self._session.execute(stmt)).scalar_one_or_none() is not None:
            raise ConflictError(f"An assessment named '{name}' already exists.")

    async def _name_taken(self, name: str) -> bool:
        stmt = select(Assessment.id).where(Assessment.name == name, Assessment.deleted_at.is_(None))
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def _generate_copy_name(self, source_name: str) -> str:
        base = f"{source_name} (Copy)"
        candidate = base
        suffix = 2
        while await self._name_taken(candidate):
            candidate = f"{base} {suffix}"
            suffix += 1
        return candidate

    async def _replace_tags(self, assessment_id: uuid.UUID, tags: list[str]) -> None:
        await self._session.execute(sa_delete(AssessmentTag).where(AssessmentTag.assessment_id == assessment_id))
        for tag in tags:
            self._session.add(AssessmentTag(assessment_id=assessment_id, tag=tag))
        await self._session.flush()

    @staticmethod
    def _to_schema(assessment: Assessment, target_count: int) -> AssessmentRead:
        return AssessmentRead(
            id=assessment.id,
            name=assessment.name,
            description=assessment.description,
            assessment_type=assessment.assessment_type,
            status=assessment.status,
            tags=sorted(tag.tag for tag in assessment.tags),
            target_count=target_count,
            started_at=assessment.started_at,
            completed_at=assessment.completed_at,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
        )
