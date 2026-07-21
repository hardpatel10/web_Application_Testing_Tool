"""assessment and target management

Revision ID: 67c183630e38
Revises: d2bf6f4862f6
Create Date: 2026-07-17 22:04:30.092327

Hand-edited after autogenerate for two reasons:

1. Alembic's autogenerate does not diff the *contents* of a ``CHECK``
   constraint, so it can't detect that ``AssessmentType``, ``AssessmentStatus``,
   and ``TargetType`` gained/renamed members. The corresponding
   ``alter_column(..., type_=...)`` calls were added by hand.

2. While investigating (1), discovered that SQLAlchemy 2.0 changed the
   default of ``Enum(create_constraint=...)`` to ``False`` — every
   ``native_enum=False`` enum column across the whole schema (going back
   to the Phase 2 migration) was a plain, unconstrained ``VARCHAR`` at the
   database level with no ``CHECK`` at all, verified with a raw-SQL insert
   that should have been rejected and wasn't. Every model's ``Enum(...)``
   call now sets ``create_constraint=True`` explicitly, and this migration
   retrofits the missing ``CHECK`` onto every previously-unconstrained
   enum column, not just the three being renamed for Phase 3.

The database is empty at the time this migration was authored (verified
before writing it), so no data-backfill step is required.

KNOWN LIMITATION — ``downgrade()`` on the ``assessments`` table: SQLite's
batch-alter reflects a table's CHECK constraints as opaque, unnamed-by-column
SQL text. Both ``status`` and ``previous_status`` are backed by the same
``AssessmentStatus`` enum, so when ``previous_status`` is dropped, SQLAlchemy's
reflection-based rebuild cannot determine that the constraint literally named
``assessmentstatus`` (auto-named after the enum, not the naming convention,
because it was added via a bare ``add_column`` rather than full table
creation) belongs to the column being dropped, and fails to rebuild the
table. Every other table's downgrade in this migration was verified to work;
this one column-drop was not resolvable within reasonable effort. For this
single-user local application, the practical rollback path is restoring
``data/app.db`` from a backup rather than ``alembic downgrade`` past this
revision — `upgrade()` (the only path exercised in normal operation) is
fully verified: applied, checked for zero model/schema drift, and confirmed
to reject invalid enum values at the database level.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '67c183630e38'
down_revision: Union[str, None] = 'd2bf6f4862f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_ASSESSMENT_TYPE = sa.Enum(
    'WEB_APPLICATION', 'NETWORK', 'API', 'MOBILE', 'CLOUD', 'WIRELESS', 'OTHER',
    name='assessmenttype', native_enum=False, length=32,
)
_NEW_ASSESSMENT_TYPE = sa.Enum(
    'NETWORK', 'WEB_APPLICATION', 'API', 'MOBILE', 'CLOUD', 'INTERNAL', 'EXTERNAL', 'CUSTOM',
    name='assessmenttype', native_enum=False, create_constraint=True, length=32,
)
_OLD_ASSESSMENT_STATUS = sa.Enum(
    'PLANNED', 'IN_PROGRESS', 'PAUSED', 'COMPLETED', 'CANCELLED',
    name='assessmentstatus', native_enum=False, length=32,
)
_NEW_ASSESSMENT_STATUS = sa.Enum(
    'DRAFT', 'READY', 'RUNNING', 'PAUSED', 'COMPLETED', 'CANCELLED', 'ARCHIVED',
    name='assessmentstatus', native_enum=False, create_constraint=True, length=32,
)
_OLD_TARGET_TYPE = sa.Enum(
    'IP', 'CIDR', 'HOSTNAME', 'DOMAIN', 'URL',
    name='targettype', native_enum=False, length=16,
)
_NEW_TARGET_TYPE = sa.Enum(
    'IPV4', 'IPV6', 'CIDR', 'HOSTNAME', 'DOMAIN', 'URL',
    name='targettype', native_enum=False, create_constraint=True, length=16,
)

# Enum value sets unchanged from Phase 2 — only adding create_constraint=True.
_OLD_TOOL_EXECUTION_STATUS = sa.Enum(
    'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED',
    name='toolexecutionstatus', native_enum=False, length=16,
)
_NEW_TOOL_EXECUTION_STATUS = sa.Enum(
    'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED',
    name='toolexecutionstatus', native_enum=False, create_constraint=True, length=16,
)
_OLD_RAW_OUTPUT_FORMAT = sa.Enum('XML', 'JSON', 'TXT', 'HTML', 'CSV', name='rawoutputformat', native_enum=False, length=8)
_NEW_RAW_OUTPUT_FORMAT = sa.Enum('XML', 'JSON', 'TXT', 'HTML', 'CSV', name='rawoutputformat', native_enum=False, create_constraint=True, length=8)
_OLD_FINDING_SEVERITY = sa.Enum('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', name='findingseverity', native_enum=False, length=16)
_NEW_FINDING_SEVERITY = sa.Enum('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', name='findingseverity', native_enum=False, create_constraint=True, length=16)
_OLD_FINDING_CONFIDENCE = sa.Enum('CONFIRMED', 'HIGH', 'MEDIUM', 'LOW', name='findingconfidence', native_enum=False, length=16)
_NEW_FINDING_CONFIDENCE = sa.Enum('CONFIRMED', 'HIGH', 'MEDIUM', 'LOW', name='findingconfidence', native_enum=False, create_constraint=True, length=16)
_OLD_FINDING_STATUS = sa.Enum('OPEN', 'CONFIRMED', 'FALSE_POSITIVE', 'ACCEPTED_RISK', 'REMEDIATED', 'DUPLICATE', name='findingstatus', native_enum=False, length=16)
_NEW_FINDING_STATUS = sa.Enum('OPEN', 'CONFIRMED', 'FALSE_POSITIVE', 'ACCEPTED_RISK', 'REMEDIATED', 'DUPLICATE', name='findingstatus', native_enum=False, create_constraint=True, length=16)
_OLD_FINDING_REFERENCE_TYPE = sa.Enum('CWE', 'OWASP', 'CAPEC', 'CVE', 'VENDOR_URL', 'DOCUMENTATION_URL', name='findingreferencetype', native_enum=False, length=32)
_NEW_FINDING_REFERENCE_TYPE = sa.Enum('CWE', 'OWASP', 'CAPEC', 'CVE', 'VENDOR_URL', 'DOCUMENTATION_URL', name='findingreferencetype', native_enum=False, create_constraint=True, length=32)
_OLD_REPORT_TYPE = sa.Enum('PDF', 'HTML', 'MARKDOWN', 'JSON', name='reporttype', native_enum=False, length=16)
_NEW_REPORT_TYPE = sa.Enum('PDF', 'HTML', 'MARKDOWN', 'JSON', name='reporttype', native_enum=False, create_constraint=True, length=16)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('assessment_history_entries',
    sa.Column('assessment_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sa.Enum('CREATED', 'UPDATED', 'STATUS_CHANGED', 'ARCHIVED', 'RESTORED', 'DELETED', 'DUPLICATED', 'TARGET_ADDED', 'TARGET_UPDATED', 'TARGET_REMOVED', 'TARGETS_IMPORTED', name='assessmenthistoryeventtype', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], name=op.f('fk_assessment_history_entries_assessment_id_assessments'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_assessment_history_entries'))
    )
    with op.batch_alter_table('assessment_history_entries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_assessment_history_entries_assessment_id'), ['assessment_id'], unique=False)
        batch_op.create_index('ix_assessment_history_entries_assessment_id_created_at', ['assessment_id', 'created_at'], unique=False)

    op.create_table('assessment_tags',
    sa.Column('assessment_id', sa.Uuid(), nullable=False),
    sa.Column('tag', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], name=op.f('fk_assessment_tags_assessment_id_assessments'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('assessment_id', 'tag', name=op.f('pk_assessment_tags'))
    )
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('previous_status', sa.Enum('DRAFT', 'READY', 'RUNNING', 'PAUSED', 'COMPLETED', 'CANCELLED', 'ARCHIVED', name='assessmentstatus', native_enum=False, create_constraint=True, length=32), nullable=True))
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column('assessment_type', existing_type=_OLD_ASSESSMENT_TYPE, type_=_NEW_ASSESSMENT_TYPE, existing_nullable=False)
        batch_op.alter_column('status', existing_type=_OLD_ASSESSMENT_STATUS, type_=_NEW_ASSESSMENT_STATUS, existing_nullable=False)
        batch_op.create_index(batch_op.f('ix_assessments_deleted_at'), ['deleted_at'], unique=False)
        batch_op.create_index('uq_assessments_name_active', ['name'], unique=True, sqlite_where=sa.text('deleted_at IS NULL'), postgresql_where=sa.text('deleted_at IS NULL'))

    with op.batch_alter_table('targets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.alter_column('target_type', existing_type=_OLD_TARGET_TYPE, type_=_NEW_TARGET_TYPE, existing_nullable=False)

    with op.batch_alter_table('tool_executions', schema=None) as batch_op:
        batch_op.alter_column('status', existing_type=_OLD_TOOL_EXECUTION_STATUS, type_=_NEW_TOOL_EXECUTION_STATUS, existing_nullable=False)

    with op.batch_alter_table('raw_tool_outputs', schema=None) as batch_op:
        batch_op.alter_column('format', existing_type=_OLD_RAW_OUTPUT_FORMAT, type_=_NEW_RAW_OUTPUT_FORMAT, existing_nullable=False)

    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.alter_column('severity', existing_type=_OLD_FINDING_SEVERITY, type_=_NEW_FINDING_SEVERITY, existing_nullable=False)
        batch_op.alter_column('confidence', existing_type=_OLD_FINDING_CONFIDENCE, type_=_NEW_FINDING_CONFIDENCE, existing_nullable=False)
        batch_op.alter_column('status', existing_type=_OLD_FINDING_STATUS, type_=_NEW_FINDING_STATUS, existing_nullable=False)

    with op.batch_alter_table('finding_references', schema=None) as batch_op:
        batch_op.alter_column('reference_type', existing_type=_OLD_FINDING_REFERENCE_TYPE, type_=_NEW_FINDING_REFERENCE_TYPE, existing_nullable=False)

    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.alter_column('report_type', existing_type=_OLD_REPORT_TYPE, type_=_NEW_REPORT_TYPE, existing_nullable=False)

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.alter_column('report_type', existing_type=_NEW_REPORT_TYPE, type_=_OLD_REPORT_TYPE, existing_nullable=False)

    with op.batch_alter_table('finding_references', schema=None) as batch_op:
        batch_op.alter_column('reference_type', existing_type=_NEW_FINDING_REFERENCE_TYPE, type_=_OLD_FINDING_REFERENCE_TYPE, existing_nullable=False)

    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.alter_column('status', existing_type=_NEW_FINDING_STATUS, type_=_OLD_FINDING_STATUS, existing_nullable=False)
        batch_op.alter_column('confidence', existing_type=_NEW_FINDING_CONFIDENCE, type_=_OLD_FINDING_CONFIDENCE, existing_nullable=False)
        batch_op.alter_column('severity', existing_type=_NEW_FINDING_SEVERITY, type_=_OLD_FINDING_SEVERITY, existing_nullable=False)

    with op.batch_alter_table('raw_tool_outputs', schema=None) as batch_op:
        batch_op.alter_column('format', existing_type=_NEW_RAW_OUTPUT_FORMAT, type_=_OLD_RAW_OUTPUT_FORMAT, existing_nullable=False)

    with op.batch_alter_table('tool_executions', schema=None) as batch_op:
        batch_op.alter_column('status', existing_type=_NEW_TOOL_EXECUTION_STATUS, type_=_OLD_TOOL_EXECUTION_STATUS, existing_nullable=False)

    with op.batch_alter_table('targets', schema=None) as batch_op:
        batch_op.alter_column('target_type', existing_type=_NEW_TARGET_TYPE, type_=_OLD_TARGET_TYPE, existing_nullable=False)
        batch_op.drop_column('enabled')

    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.drop_index('uq_assessments_name_active', sqlite_where=sa.text('deleted_at IS NULL'), postgresql_where=sa.text('deleted_at IS NULL'))
        batch_op.drop_index(batch_op.f('ix_assessments_deleted_at'))
        # previous_status/deleted_at are dropped in their own batch block,
        # separate from the status/assessment_type alter_column calls below:
        # combining a drop_column for a column with an enum-derived CHECK
        # constraint and an alter_column for a *different* column sharing
        # the same Enum ``name=`` in one batch confuses SQLAlchemy's
        # reflect-and-rebuild step. It also cannot infer, from a reflected
        # table, that the table-level CHECK constraint named
        # 'assessmentstatus' depends on the previous_status column being
        # dropped, so that constraint must be dropped explicitly first.
        batch_op.drop_constraint('assessmentstatus', type_='check')
        batch_op.drop_column('deleted_at')
        batch_op.drop_column('previous_status')

    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.alter_column('status', existing_type=_NEW_ASSESSMENT_STATUS, type_=_OLD_ASSESSMENT_STATUS, existing_nullable=False)
        batch_op.alter_column('assessment_type', existing_type=_NEW_ASSESSMENT_TYPE, type_=_OLD_ASSESSMENT_TYPE, existing_nullable=False)

    op.drop_table('assessment_tags')
    with op.batch_alter_table('assessment_history_entries', schema=None) as batch_op:
        batch_op.drop_index('ix_assessment_history_entries_assessment_id_created_at')
        batch_op.drop_index(batch_op.f('ix_assessment_history_entries_assessment_id'))

    op.drop_table('assessment_history_entries')
    # ### end Alembic commands ###
