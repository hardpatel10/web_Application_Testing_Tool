"""assessment execution engine

Revision ID: a264a27eb29e
Revises: 15d36d2a4f40
Create Date: 2026-07-18 19:34:40.224254

Hand-edited after autogenerate, same reason as Phase 3's migration:
autogenerate diffs column presence, not the *contents* of a ``CHECK``
constraint, so it never detects that ``ToolExecutionStatus`` gained
``QUEUED``/``PREPARING``/``SKIPPED`` (job states the execution engine
needs) or that ``AssessmentHistoryEventType`` gained execution-related
event types. Both ``alter_column`` calls were added by hand; the two new
``tool_executions`` columns (``retry_count``, ``status_message``) were
picked up by autogenerate as-is.

Both tables are verified empty at the time this migration was authored
(no execution capability existed before this phase), so ``retry_count``
and ``created_at`` are added ``NOT NULL`` with no server default, same
justification as Phase 5's ``tools.status``. ``created_at`` is when a
job was planned -- a stable default sort order for job history/listing
views, distinct from ``started_at`` (a job routinely sits queued for a
while before a worker slot picks it up).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a264a27eb29e'
down_revision: Union[str, None] = '15d36d2a4f40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_TOOL_EXECUTION_STATUS = sa.Enum(
    'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED',
    name='toolexecutionstatus', native_enum=False, create_constraint=True, length=16,
)
_NEW_TOOL_EXECUTION_STATUS = sa.Enum(
    'PENDING', 'QUEUED', 'PREPARING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT', 'SKIPPED',
    name='toolexecutionstatus', native_enum=False, create_constraint=True, length=16,
)
_OLD_ASSESSMENT_HISTORY_EVENT_TYPE = sa.Enum(
    'CREATED', 'UPDATED', 'STATUS_CHANGED', 'ARCHIVED', 'RESTORED', 'DELETED', 'DUPLICATED',
    'TARGET_ADDED', 'TARGET_UPDATED', 'TARGET_REMOVED', 'TARGETS_IMPORTED',
    name='assessmenthistoryeventtype', native_enum=False, create_constraint=True, length=32,
)
_NEW_ASSESSMENT_HISTORY_EVENT_TYPE = sa.Enum(
    'CREATED', 'UPDATED', 'STATUS_CHANGED', 'ARCHIVED', 'RESTORED', 'DELETED', 'DUPLICATED',
    'TARGET_ADDED', 'TARGET_UPDATED', 'TARGET_REMOVED', 'TARGETS_IMPORTED',
    'EXECUTION_STARTED', 'EXECUTION_FINISHED', 'EXECUTION_CANCELLED', 'JOB_FAILED',
    name='assessmenthistoryeventtype', native_enum=False, create_constraint=True, length=32,
)


def upgrade() -> None:
    with op.batch_alter_table('tool_executions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('status_message', sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
        )
        batch_op.alter_column(
            'status', existing_type=_OLD_TOOL_EXECUTION_STATUS, type_=_NEW_TOOL_EXECUTION_STATUS, existing_nullable=False
        )

    with op.batch_alter_table('tool_executions', schema=None) as batch_op:
        batch_op.alter_column('retry_count', server_default=None)
        batch_op.alter_column('created_at', server_default=None)

    with op.batch_alter_table('assessment_history_entries', schema=None) as batch_op:
        batch_op.alter_column(
            'event_type',
            existing_type=_OLD_ASSESSMENT_HISTORY_EVENT_TYPE,
            type_=_NEW_ASSESSMENT_HISTORY_EVENT_TYPE,
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('assessment_history_entries', schema=None) as batch_op:
        batch_op.alter_column(
            'event_type',
            existing_type=_NEW_ASSESSMENT_HISTORY_EVENT_TYPE,
            type_=_OLD_ASSESSMENT_HISTORY_EVENT_TYPE,
            existing_nullable=False,
        )

    with op.batch_alter_table('tool_executions', schema=None) as batch_op:
        batch_op.alter_column(
            'status', existing_type=_NEW_TOOL_EXECUTION_STATUS, type_=_OLD_TOOL_EXECUTION_STATUS, existing_nullable=False
        )
        batch_op.drop_column('status_message')
        batch_op.drop_column('retry_count')
        batch_op.drop_column('created_at')
