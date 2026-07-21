"""Shared helper: exclude rows whose owning ``Assessment`` has been soft-deleted.

``AssessmentService.delete()`` is a soft delete -- it never removes the
``Assessment`` row or any of its descendant data (see that method's own
docstring: "cleanup of deleted assessments' data is explicitly deferred to
a later phase"). There is no DB-level cascade for "deleted means invisible";
every read-side query across the dashboard, host inventory, findings,
search, and execution history must exclude a soft-deleted assessment's data
itself, the same way :class:`~backend.services.assessment_service.AssessmentService`
already does for the ``Assessment`` rows themselves.

Two shapes, matching the two ways a table is scoped to an assessment in
this schema: some tables carry ``assessment_id`` directly (``Target``,
``DiscoveredHost``, ``Finding``, ``ToolExecution``, ``Report``); others only
carry ``host_id`` and reach their assessment through ``DiscoveredHost``
(``Service``, ``Technology``, ``OperatingSystem``, ``Observation``).
"""

from sqlalchemy import ColumnElement, select

from backend.models.assessment import Assessment
from backend.models.discovered_host import DiscoveredHost


def owned_by_active_assessment(assessment_id_column: ColumnElement) -> ColumnElement:
    """Condition: ``assessment_id_column`` points at an assessment that is not soft-deleted."""
    return assessment_id_column.in_(select(Assessment.id).where(Assessment.deleted_at.is_(None)))


def host_owned_by_active_assessment(host_id_column: ColumnElement) -> ColumnElement:
    """Condition: ``host_id_column`` points at a ``DiscoveredHost`` whose assessment is not soft-deleted."""
    active_hosts = (
        select(DiscoveredHost.id)
        .join(Assessment, Assessment.id == DiscoveredHost.assessment_id)
        .where(Assessment.deleted_at.is_(None))
    )
    return host_id_column.in_(active_hosts)
