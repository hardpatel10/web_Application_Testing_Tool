"""correlation_engine_and_findings

Revision ID: f3a9c1d5e7b2
Revises: d151c8e205d2
Create Date: 2026-07-19 14:00:00.000000

Phase 9: builds the Correlation Engine's persistence layer on top of
Phase 8's frozen inventory tables (``assets``/``services``/``technologies``/
``operating_systems``/``observations``) -- none of which this migration
touches.

``findings``/``finding_evidence``/``finding_references`` have existed,
completely unused, since Phase 2's original migration -- verified directly
against this project's real dev database immediately before writing this
migration (``SELECT COUNT(*) FROM findings`` = 0, and both child tables can
only be non-empty if ``findings`` is). With zero rows on the line, this is
the one migration so far that gets to be a plain drop-and-recreate instead
of Phase 8's three-pass additive-column/backfill/tighten dance -- there is
nothing to preserve. A defensive row-count guard still runs first and
aborts ``upgrade()`` rather than silently discarding data if that
assumption is ever wrong on some other database.

Adds two new tables: ``finding_observations`` (the "all observation
references" join table a merged finding's evidence trail requires) and
``correlation_runs`` (a durable history log of every Correlation Engine
pass, backing ``GET /correlation/status``).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f3a9c1d5e7b2'
down_revision: Union[str, None] = 'd151c8e205d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _assert_findings_table_is_empty() -> None:
    bind = op.get_bind()
    count = bind.execute(sa.text("SELECT COUNT(*) FROM findings")).scalar_one()
    if count:
        raise RuntimeError(
            f"Refusing to run: 'findings' has {count} existing row(s). This migration was written "
            "assuming an empty table (true for every session through Phase 8) and drops/recreates it "
            "without a data-preserving backfill path."
        )


def upgrade() -> None:
    _assert_findings_table_is_empty()

    op.drop_table('finding_references')
    op.drop_table('finding_evidence')
    op.drop_table('findings')

    op.create_table(
        'findings',
        sa.Column('assessment_id', sa.Uuid(), nullable=False),
        sa.Column('asset_id', sa.Uuid(), nullable=True),
        sa.Column('source_execution_id', sa.Uuid(), nullable=True),
        sa.Column('rule_id', sa.String(length=64), nullable=False),
        sa.Column('plugin', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('impact', sa.Text(), nullable=True),
        sa.Column(
            'severity',
            sa.Enum('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', name='findingseverity', native_enum=False, create_constraint=True, length=16),
            nullable=False,
        ),
        sa.Column(
            'confidence',
            sa.Enum('CONFIRMED', 'HIGH', 'MEDIUM', 'LOW', name='findingconfidence', native_enum=False, create_constraint=True, length=16),
            nullable=False,
        ),
        sa.Column('category', sa.String(length=32), nullable=True),
        sa.Column('cvss_score', sa.Float(), nullable=True),
        sa.Column('cwe', sa.String(length=20), nullable=True),
        sa.Column('owasp', sa.String(length=20), nullable=True),
        sa.Column('remediation', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('OPEN', 'CONFIRMED', 'FALSE_POSITIVE', 'ACCEPTED_RISK', 'REMEDIATED', 'DUPLICATE', name='findingstatus', native_enum=False, create_constraint=True, length=16),
            nullable=False,
        ),
        sa.Column('fingerprint', sa.String(length=80), nullable=False),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('cvss_score IS NULL OR (cvss_score >= 0 AND cvss_score <= 10)', name=op.f('ck_findings_cvss_score_range')),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], name=op.f('fk_findings_assessment_id_assessments'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], name=op.f('fk_findings_asset_id_assets'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_execution_id'], ['tool_executions.id'], name=op.f('fk_findings_source_execution_id_tool_executions'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_findings')),
    )
    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.create_index('uq_findings_assessment_id_fingerprint', ['assessment_id', 'fingerprint'], unique=True)
        batch_op.create_index('ix_findings_assessment_id_severity', ['assessment_id', 'severity'], unique=False)
        batch_op.create_index('ix_findings_asset_id_severity', ['asset_id', 'severity'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_assessment_id'), ['assessment_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_asset_id'), ['asset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_source_execution_id'), ['source_execution_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_rule_id'), ['rule_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_plugin'), ['plugin'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_severity'), ['severity'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_status'), ['status'], unique=False)

    op.create_table(
        'finding_evidence',
        sa.Column('finding_id', sa.Uuid(), nullable=False),
        sa.Column('source_tool', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=1024), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], name=op.f('fk_finding_evidence_finding_id_findings'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_finding_evidence')),
    )
    with op.batch_alter_table('finding_evidence', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_finding_evidence_finding_id'), ['finding_id'], unique=False)

    op.create_table(
        'finding_references',
        sa.Column('finding_id', sa.Uuid(), nullable=False),
        sa.Column(
            'reference_type',
            sa.Enum('CWE', 'OWASP', 'CAPEC', 'CVE', 'VENDOR_URL', 'DOCUMENTATION_URL', name='findingreferencetype', native_enum=False, create_constraint=True, length=32),
            nullable=False,
        ),
        sa.Column('reference_value', sa.String(length=255), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], name=op.f('fk_finding_references_finding_id_findings'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_finding_references')),
    )
    with op.batch_alter_table('finding_references', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_finding_references_finding_id'), ['finding_id'], unique=False)
        batch_op.create_index('uq_finding_references_finding_id_type_value', ['finding_id', 'reference_type', 'reference_value'], unique=True)

    op.create_table(
        'finding_observations',
        sa.Column('finding_id', sa.Uuid(), nullable=False),
        sa.Column('observation_id', sa.Uuid(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], name=op.f('fk_finding_observations_finding_id_findings'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['observation_id'], ['observations.id'], name=op.f('fk_finding_observations_observation_id_observations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_finding_observations')),
    )
    with op.batch_alter_table('finding_observations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_finding_observations_finding_id'), ['finding_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_finding_observations_observation_id'), ['observation_id'], unique=False)
        batch_op.create_index('uq_finding_observations_finding_id_observation_id', ['finding_id', 'observation_id'], unique=True)

    op.create_table(
        'correlation_runs',
        sa.Column('assessment_id', sa.Uuid(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('RUNNING', 'COMPLETED', 'FAILED', name='correlationrunstatus', native_enum=False, create_constraint=True, length=16),
            nullable=False,
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assets_evaluated', sa.Integer(), nullable=False),
        sa.Column('rules_evaluated', sa.Integer(), nullable=False),
        sa.Column('findings_created', sa.Integer(), nullable=False),
        sa.Column('findings_updated', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], name=op.f('fk_correlation_runs_assessment_id_assessments'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_correlation_runs')),
    )
    with op.batch_alter_table('correlation_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_correlation_runs_assessment_id'), ['assessment_id'], unique=False)


def downgrade() -> None:
    op.drop_table('correlation_runs')

    with op.batch_alter_table('finding_observations', schema=None) as batch_op:
        batch_op.drop_index('uq_finding_observations_finding_id_observation_id')
        batch_op.drop_index(batch_op.f('ix_finding_observations_observation_id'))
        batch_op.drop_index(batch_op.f('ix_finding_observations_finding_id'))
    op.drop_table('finding_observations')

    with op.batch_alter_table('finding_references', schema=None) as batch_op:
        batch_op.drop_index('uq_finding_references_finding_id_type_value')
        batch_op.drop_index(batch_op.f('ix_finding_references_finding_id'))
    op.drop_table('finding_references')

    with op.batch_alter_table('finding_evidence', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_finding_evidence_finding_id'))
    op.drop_table('finding_evidence')

    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_findings_status'))
        batch_op.drop_index(batch_op.f('ix_findings_severity'))
        batch_op.drop_index(batch_op.f('ix_findings_category'))
        batch_op.drop_index(batch_op.f('ix_findings_plugin'))
        batch_op.drop_index(batch_op.f('ix_findings_rule_id'))
        batch_op.drop_index(batch_op.f('ix_findings_source_execution_id'))
        batch_op.drop_index(batch_op.f('ix_findings_asset_id'))
        batch_op.drop_index(batch_op.f('ix_findings_assessment_id'))
        batch_op.drop_index('ix_findings_asset_id_severity')
        batch_op.drop_index('ix_findings_assessment_id_severity')
        batch_op.drop_index('uq_findings_assessment_id_fingerprint')
    op.drop_table('findings')

    op.create_table(
        'findings',
        sa.Column('execution_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.Enum('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', name='findingseverity', native_enum=False, length=16), nullable=False),
        sa.Column('confidence', sa.Enum('CONFIRMED', 'HIGH', 'MEDIUM', 'LOW', name='findingconfidence', native_enum=False, length=16), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('cvss_score', sa.Float(), nullable=True),
        sa.Column('cwe', sa.String(length=20), nullable=True),
        sa.Column('owasp', sa.String(length=20), nullable=True),
        sa.Column('remediation', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('OPEN', 'CONFIRMED', 'FALSE_POSITIVE', 'ACCEPTED_RISK', 'REMEDIATED', 'DUPLICATE', name='findingstatus', native_enum=False, length=16), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('cvss_score IS NULL OR (cvss_score >= 0 AND cvss_score <= 10)', name=op.f('ck_findings_cvss_score_range')),
        sa.ForeignKeyConstraint(['execution_id'], ['tool_executions.id'], name=op.f('fk_findings_execution_id_tool_executions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_findings')),
    )
    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_findings_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_execution_id'), ['execution_id'], unique=False)
        batch_op.create_index('ix_findings_execution_id_severity', ['execution_id', 'severity'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_severity'), ['severity'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_status'), ['status'], unique=False)

    op.create_table(
        'finding_evidence',
        sa.Column('finding_id', sa.Uuid(), nullable=False),
        sa.Column('source_tool', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=1024), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], name=op.f('fk_finding_evidence_finding_id_findings'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_finding_evidence')),
    )
    with op.batch_alter_table('finding_evidence', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_finding_evidence_finding_id'), ['finding_id'], unique=False)

    op.create_table(
        'finding_references',
        sa.Column('finding_id', sa.Uuid(), nullable=False),
        sa.Column('reference_type', sa.Enum('CWE', 'OWASP', 'CAPEC', 'CVE', 'VENDOR_URL', 'DOCUMENTATION_URL', name='findingreferencetype', native_enum=False, length=32), nullable=False),
        sa.Column('reference_value', sa.String(length=255), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], name=op.f('fk_finding_references_finding_id_findings'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_finding_references')),
    )
    with op.batch_alter_table('finding_references', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_finding_references_finding_id'), ['finding_id'], unique=False)
        batch_op.create_index('uq_finding_references_finding_id_type_value', ['finding_id', 'reference_type', 'reference_value'], unique=True)
