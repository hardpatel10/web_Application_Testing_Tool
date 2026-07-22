"""assessment pipeline engine

Revision ID: a4e6f1c2d8b7
Revises: d12d16aab9d9
Create Date: 2026-07-21 22:59:07.061937

Phase 12: builds the Assessment Pipeline's persistence layer.

Two new tables:

- ``pipeline_runs`` -- one durable record per "Start Assessment" pipeline
  trigger (mirrors ``correlation_runs``' role for the Correlation Engine).
- ``pipeline_jobs`` -- one execution-graph node per run (recon/scan/correlate
  stage), each either carrying a real ``execution_id`` (a follow-up scanner
  actually scheduled) or standing alone as a pure ``SKIPPED`` record (a
  reserved-for-later scanner, or "no supported web services discovered").

Plus two additive, nullable/defaulted columns on the pre-existing ``targets``
table so the Pipeline Engine can generate synthetic endpoint targets (e.g.
``http://host:80``) that reuse the existing ``ExecutionPlanner``/
``ExecutionManager`` machinery unmodified, while staying excluded from the
user-facing Targets tab/picker:

- ``targets.origin`` ('user'/'pipeline', default 'user' -- every existing row
  reads 'user', which is correct: nothing before this phase ever generated a
  target).
- ``targets.discovered_from_execution_id`` (nullable FK -> tool_executions,
  SET NULL) -- which recon execution generated this target, null for every
  pre-existing (user-added) target.

Safe to apply against the real dev database (verified: `data/app.db` backed
up beforehand as `data/app.db.bak-phase12-<timestamp>`).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a4e6f1c2d8b7'
down_revision: Union[str, None] = 'd12d16aab9d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pipeline_runs',
        sa.Column('assessment_id', sa.Uuid(), nullable=False),
        sa.Column('recon_execution_id', sa.Uuid(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('RUNNING', 'COMPLETED', 'FAILED', name='pipelinerunstatus', native_enum=False, create_constraint=True, length=16),
            nullable=False,
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], name=op.f('fk_pipeline_runs_assessment_id_assessments'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recon_execution_id'], ['tool_executions.id'], name=op.f('fk_pipeline_runs_recon_execution_id_tool_executions'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_pipeline_runs')),
    )
    with op.batch_alter_table('pipeline_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pipeline_runs_assessment_id'), ['assessment_id'], unique=False)

    op.create_table(
        'pipeline_jobs',
        sa.Column('pipeline_run_id', sa.Uuid(), nullable=False),
        sa.Column(
            'stage',
            sa.Enum('RECON', 'SCAN', 'CORRELATE', name='pipelinestage', native_enum=False, create_constraint=True, length=16),
            nullable=False,
        ),
        sa.Column('tool_name', sa.String(length=100), nullable=True),
        sa.Column('host_id', sa.Uuid(), nullable=True),
        sa.Column('service_id', sa.Uuid(), nullable=True),
        sa.Column('execution_id', sa.Uuid(), nullable=True),
        sa.Column('target_value', sa.String(length=512), nullable=True),
        sa.Column(
            'status',
            sa.Enum('WAITING', 'RUNNING', 'SKIPPED', 'COMPLETED', 'FAILED', name='pipelinejobstatus', native_enum=False, create_constraint=True, length=16),
            nullable=False,
        ),
        sa.Column('skip_reason', sa.Text(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_runs.id'], name=op.f('fk_pipeline_jobs_pipeline_run_id_pipeline_runs'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['host_id'], ['discovered_hosts.id'], name=op.f('fk_pipeline_jobs_host_id_discovered_hosts'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], name=op.f('fk_pipeline_jobs_service_id_services'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['execution_id'], ['tool_executions.id'], name=op.f('fk_pipeline_jobs_execution_id_tool_executions'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_pipeline_jobs')),
    )
    with op.batch_alter_table('pipeline_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pipeline_jobs_pipeline_run_id'), ['pipeline_run_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pipeline_jobs_host_id'), ['host_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pipeline_jobs_execution_id'), ['execution_id'], unique=False)

    with op.batch_alter_table('targets', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'origin',
                sa.Enum('USER', 'PIPELINE', name='targetorigin', native_enum=False, create_constraint=True, length=16),
                nullable=False,
                server_default='USER',
            )
        )
        batch_op.add_column(sa.Column('discovered_from_execution_id', sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f('fk_targets_discovered_from_execution_id_tool_executions'),
            'tool_executions', ['discovered_from_execution_id'], ['id'], ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('targets', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_targets_discovered_from_execution_id_tool_executions'), type_='foreignkey')
        batch_op.drop_column('discovered_from_execution_id')
        batch_op.drop_column('origin')

    with op.batch_alter_table('pipeline_jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pipeline_jobs_execution_id'))
        batch_op.drop_index(batch_op.f('ix_pipeline_jobs_host_id'))
        batch_op.drop_index(batch_op.f('ix_pipeline_jobs_pipeline_run_id'))
    op.drop_table('pipeline_jobs')

    with op.batch_alter_table('pipeline_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pipeline_runs_assessment_id'))
    op.drop_table('pipeline_runs')
