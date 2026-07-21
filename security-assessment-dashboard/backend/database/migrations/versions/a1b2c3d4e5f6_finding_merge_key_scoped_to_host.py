"""finding_merge_key_scoped_to_host

Revision ID: a1b2c3d4e5f6
Revises: fb8c47562214
Create Date: 2026-07-20 12:00:00.000000

Bug fix: the Correlation Engine's Finding upsert (``CorrelationService._upsert_finding``)
looked up "have I already created this finding" by ``(assessment_id, fingerprint)``
alone. ``fingerprint`` is derived purely from host *identity* (MAC/IP/hostname --
see ``backend.services.fingerprinting.host_fingerprint``), which is not itself
scoped to the ``Target`` that discovered it: per ``fb8c47562214``, the same
physical host can legitimately back two different ``DiscoveredHost`` rows in
one assessment (e.g. added once as its own target, and again swept inside a
CIDR target). Without ``host_id`` in the lookup/unique key, correlating the
second host's identical rule match found the first host's ``Finding`` row and
silently merged onto it -- collapsing two different Assessment Targets'
evidence onto one finding.

This migration (and the matching ``CorrelationService`` code change) moves
the merge key to ``(assessment_id, host_id, fingerprint)`` -- one rule fires
at most once per *host*, not once per assessment-wide fingerprint collision.
SQLite/Postgres both treat NULL as distinct in a unique index, so the
existing (currently unused) NULL-``host_id`` "assessment-wide rule" case is
unaffected.

No data migration needed: existing ``findings`` rows already have their real
``host_id`` set (it has been NOT NULL in practice since the correlation
engine was introduced), so the new, stricter index accepts every existing
row as-is -- there is nothing to backfill or de-duplicate.
"""

from typing import Sequence, Union

from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'fb8c47562214'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.drop_index('uq_findings_assessment_id_fingerprint')
        batch_op.create_index(
            'uq_findings_assessment_id_host_id_fingerprint',
            ['assessment_id', 'host_id', 'fingerprint'],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.drop_index('uq_findings_assessment_id_host_id_fingerprint')
        batch_op.create_index(
            'uq_findings_assessment_id_fingerprint', ['assessment_id', 'fingerprint'], unique=True
        )
