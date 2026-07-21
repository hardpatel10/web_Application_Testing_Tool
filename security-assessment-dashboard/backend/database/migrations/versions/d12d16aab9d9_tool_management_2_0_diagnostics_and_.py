"""tool management 2.0 diagnostics and profile enable/disable

Revision ID: d12d16aab9d9
Revises: a1b2c3d4e5f6
Create Date: 2026-07-21 12:00:46.791191

Two additive, nullable columns for Phase 10 (Tool Management 2.0):

- ``tools.last_validated_at`` — when POST /tools/{name}/validate (or the
  bulk /tools/validate) last ran for this tool. Distinct from the
  pre-existing ``last_checked_at`` (a health check), since validation
  additionally checks version support, permissions, and dependencies.
- ``tool_configurations.disabled_profiles_json`` — Scan Profile ids the
  user has disabled for this tool (see
  ``backend.plugins.models.config.PluginConfiguration.disabled_profile_ids``).
  A disabled profile still exists and can be viewed/exported, it's just
  not offered for new scans.

Both are nullable with no backfill needed — every existing ``tools`` /
``tool_configurations`` row simply reads ``NULL`` (never validated /
nothing disabled) until the corresponding action happens, which is the
correct, honest default. Safe to apply against the real dev database
(verified: `data/app.db` backed up beforehand as
`data/app.db.bak-phase10-20260721120041`).

An unrelated index-name normalization on ``execution_hosts``
(autogenerate noticed ``ix_execution_assets_execution_id`` still uses its
pre-rename name from the Asset->DiscoveredHost migration) was dropped
from this migration on review — cosmetic, unrelated to Tool Management,
and left for a future pass rather than bundled in here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd12d16aab9d9'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tool_configurations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('disabled_profiles_json', sa.JSON(), nullable=True))

    with op.batch_alter_table('tools', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('tools', schema=None) as batch_op:
        batch_op.drop_column('last_validated_at')

    with op.batch_alter_table('tool_configurations', schema=None) as batch_op:
        batch_op.drop_column('disabled_profiles_json')
