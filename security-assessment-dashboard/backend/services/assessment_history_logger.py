"""Shared helper for writing assessment history entries.

Kept as a standalone function rather than a method on ``AssessmentService``
so ``TargetService`` can log target-related events (added/updated/removed/
imported) onto an assessment's activity log without depending on the whole
``AssessmentService``.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.assessment_history import AssessmentHistoryEntry
from backend.models.enums import AssessmentHistoryEventType


async def log_assessment_event(
    session: AsyncSession,
    assessment_id: uuid.UUID,
    event_type: AssessmentHistoryEventType,
    message: str,
) -> None:
    """Append one append-only entry to an assessment's activity log."""
    entry = AssessmentHistoryEntry(assessment_id=assessment_id, event_type=event_type, message=message)
    session.add(entry)
    await session.flush()
