"""target_owned_discovered_hosts

Revision ID: fb8c47562214
Revises: f3a9c1d5e7b2
Create Date: 2026-07-19 16:30:00.000000

Domain-model correction: the platform is a Security Assessment Platform, not
an Asset Discovery platform. ``Asset`` previously hung directly off
``Assessment`` (``assets.assessment_id``) as a sibling of ``Target``, with no
FK path back to the ``Target`` that actually discovered it -- structurally
indistinguishable from treating discovered hosts as the assessment's primary
subject, when the user-supplied ``Target`` (example.com, 192.168.1.0/24, ...)
is the real assessment scope. This migration makes ``Target`` the true parent:

    Assessment -> Target -> Execution -> DiscoveredHost -> Services/Technologies/
    OperatingSystems/Observations -> Correlation -> Findings

Renames throughout (pure renames, no behavior change beyond the new FK):
``assets`` -> ``discovered_hosts``, ``execution_assets`` -> ``execution_hosts``,
every dependent table's ``asset_id`` FK -> ``host_id`` (``services``,
``technologies``, ``operating_systems``, ``network_interfaces``,
``observations``, ``findings``, ``fingerprints``), ``assets.asset_type`` ->
``discovered_hosts.host_type``, ``correlation_runs.assets_evaluated`` ->
``hosts_evaluated``.

The real behavior change: ``discovered_hosts`` gains a ``target_id`` column
(nullable -- see below) and its dedup/merge key moves from
``(assessment_id, fingerprint)`` to ``(target_id, fingerprint)`` -- a host
discovered under two different targets in the same assessment (e.g. added
once as its own target, and again swept by a CIDR target) is now two
separate ``DiscoveredHost`` rows, matching "hosts are children of the target
that found them," per ``.claude/CLAUDE.md``'s corrected domain model.
``assessment_id`` stays on the table too, denormalized exactly like
``ToolExecution.assessment_id``/``target_id`` already are, for cheap
per-assessment scoping without a join through ``targets``.

Backfill for pre-existing rows: ``target_id`` is resolved via
``source_execution_id -> tool_executions.target_id`` first, falling back to
the earliest ``execution_hosts`` link's execution if ``source_execution_id``
is unset or dangling. Per this project's established "skip rather than
guess" precedent (see ``d151c8e205d2``'s asset backfill), a host with no
resolvable execution history at all is left with ``target_id IS NULL``
instead of an invented association -- verified directly against this
project's real dev database immediately before writing this migration: all
10 existing ``assets`` rows had a cleanly resolvable target via
``source_execution_id``, so the fallback/skip paths are defensive, not
exercised by any known data.

SQLite auto-rewrites other tables' foreign key *definitions* when the table
they reference is renamed (confirmed directly against this project's real
dev database copy before writing this migration) -- so renaming ``assets`` ->
``discovered_hosts`` happens first, before any dependent table's
``asset_id`` -> ``host_id`` column rename, and each dependent table's FK
already points at ``discovered_hosts`` by the time its own batch-mode
recreate reflects it.
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'fb8c47562214'
down_revision: Union[str, None] = 'f3a9c1d5e7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Pass 1: rename the two tables whose name itself was wrong -------------
    op.rename_table('assets', 'discovered_hosts')
    op.rename_table('execution_assets', 'execution_hosts')

    # -- Pass 2: additive nullable target_id + asset_type -> host_type rename --
    #
    # The two pre-existing CHECK constraints on asset_type ('ck_assets_assettype',
    # plus a stray pre-naming-convention 'assettype' duplicate -- both visible on
    # this project's real dev database) hardcode the *old* column name in their
    # raw SQL text; Alembic's SQLite batch-mode recreate cannot rewrite arbitrary
    # CHECK expression text, so both must be dropped explicitly before the rename
    # and replaced with a freshly named one after it (same class of limitation
    # this project's own migrations already document for enum-column downgrades).
    with op.batch_alter_table('discovered_hosts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('target_id', sa.Uuid(), nullable=True))
        batch_op.drop_constraint(sa.schema.conv('ck_assets_assettype'), type_='check')
        batch_op.drop_constraint(sa.schema.conv('assettype'), type_='check')
        batch_op.alter_column('asset_type', new_column_name='host_type', existing_type=sa.VARCHAR(length=16))
        batch_op.create_check_constraint(sa.schema.conv('ck_discovered_hosts_hosttype'), "host_type IN ('HOST', 'WEBSITE', 'API', 'DOMAIN', 'IP')")

    # -- Pass 3: backfill target_id for every pre-existing row -----------------
    _backfill_target_id(op.get_bind())

    # -- Pass 4: discovered_hosts' new merge key + target_id FK ----------------
    with op.batch_alter_table('discovered_hosts', schema=None) as batch_op:
        batch_op.drop_index('uq_assets_assessment_id_fingerprint')
        batch_op.drop_index('ix_assets_assessment_id')
        batch_op.drop_index('ix_assets_ipv4')
        batch_op.drop_index('ix_assets_ipv6')
        batch_op.drop_index('ix_assets_source_execution_id')
        batch_op.create_index(batch_op.f('ix_discovered_hosts_assessment_id'), ['assessment_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_discovered_hosts_ipv4'), ['ipv4'], unique=False)
        batch_op.create_index(batch_op.f('ix_discovered_hosts_ipv6'), ['ipv6'], unique=False)
        batch_op.create_index(batch_op.f('ix_discovered_hosts_source_execution_id'), ['source_execution_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_discovered_hosts_target_id'), ['target_id'], unique=False)
        batch_op.create_index('uq_discovered_hosts_target_id_fingerprint', ['target_id', 'fingerprint'], unique=True)
        batch_op.create_foreign_key(
            batch_op.f('fk_discovered_hosts_target_id_targets'), 'targets', ['target_id'], ['id'], ondelete='CASCADE'
        )

    # -- Pass 5: every dependent table's asset_id -> host_id --------------------
    #
    # Each table gets its own *two* batch blocks (drop old indexes + rename
    # column, then create the new-named indexes in a second block) rather than
    # one combined block -- combining them confused batch mode's automatic
    # "carry forward every other untouched index" reconciliation (it resolves
    # new indexes against columns by name at flush time, before the rename in
    # the same block had actually landed), discovered by running this
    # migration directly against this project's real dev database.
    with op.batch_alter_table('execution_hosts', schema=None) as batch_op:
        batch_op.drop_index('uq_execution_assets_execution_id_asset_id')
        batch_op.drop_index('ix_execution_assets_asset_id')
        batch_op.alter_column('asset_id', new_column_name='host_id', existing_type=sa.Uuid())
    with op.batch_alter_table('execution_hosts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_execution_hosts_host_id'), ['host_id'], unique=False)
        batch_op.create_index('uq_execution_hosts_execution_id_host_id', ['execution_id', 'host_id'], unique=True)

    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.drop_index('uq_services_asset_id_fingerprint')
        batch_op.drop_index('ix_services_asset_id')
        batch_op.alter_column('asset_id', new_column_name='host_id', existing_type=sa.Uuid())
    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_services_host_id'), ['host_id'], unique=False)
        batch_op.create_index('uq_services_host_id_fingerprint', ['host_id', 'fingerprint'], unique=True)

    with op.batch_alter_table('technologies', schema=None) as batch_op:
        batch_op.drop_index('uq_technologies_asset_id_service_id_name')
        batch_op.drop_index('ix_technologies_asset_id')
        batch_op.alter_column('asset_id', new_column_name='host_id', existing_type=sa.Uuid())
    with op.batch_alter_table('technologies', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_technologies_host_id'), ['host_id'], unique=False)
        batch_op.create_index('uq_technologies_host_id_service_id_name', ['host_id', 'service_id', 'name'], unique=True)

    with op.batch_alter_table('operating_systems', schema=None) as batch_op:
        batch_op.drop_index('uq_operating_systems_asset_id_name_version')
        batch_op.drop_index('ix_operating_systems_asset_id')
        batch_op.alter_column('asset_id', new_column_name='host_id', existing_type=sa.Uuid())
    with op.batch_alter_table('operating_systems', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_operating_systems_host_id'), ['host_id'], unique=False)
        batch_op.create_index('uq_operating_systems_host_id_name_version', ['host_id', 'name', 'version'], unique=True)

    with op.batch_alter_table('network_interfaces', schema=None) as batch_op:
        batch_op.drop_index('uq_network_interfaces_asset_id_ip_address')
        batch_op.drop_index('ix_network_interfaces_asset_id')
        batch_op.alter_column('asset_id', new_column_name='host_id', existing_type=sa.Uuid())
    with op.batch_alter_table('network_interfaces', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_network_interfaces_host_id'), ['host_id'], unique=False)
        batch_op.create_index('uq_network_interfaces_host_id_ip_address', ['host_id', 'ip_address'], unique=True)

    with op.batch_alter_table('observations', schema=None) as batch_op:
        batch_op.drop_index('uq_observations_asset_id_fingerprint')
        batch_op.drop_index('ix_observations_asset_id')
        batch_op.alter_column('asset_id', new_column_name='host_id', existing_type=sa.Uuid())
    with op.batch_alter_table('observations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_observations_host_id'), ['host_id'], unique=False)
        batch_op.create_index('uq_observations_host_id_fingerprint', ['host_id', 'fingerprint'], unique=True)

    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.drop_index('ix_findings_asset_id_severity')
        batch_op.drop_index('ix_findings_asset_id')
        batch_op.alter_column('asset_id', new_column_name='host_id', existing_type=sa.Uuid())
    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_findings_host_id'), ['host_id'], unique=False)
        batch_op.create_index('ix_findings_host_id_severity', ['host_id', 'severity'], unique=False)

    with op.batch_alter_table('fingerprints', schema=None) as batch_op:
        batch_op.drop_index('ix_fingerprints_asset_id')
        # Same raw-CHECK-text limitation as discovered_hosts.asset_type above:
        # 'fingerprint_has_owner' hardcodes 'asset_id' in its SQL expression.
        batch_op.drop_constraint(sa.schema.conv('ck_fingerprints_fingerprint_has_owner'), type_='check')
        batch_op.alter_column('asset_id', new_column_name='host_id', existing_type=sa.Uuid())
    with op.batch_alter_table('fingerprints', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_fingerprints_host_id'), ['host_id'], unique=False)
        batch_op.create_check_constraint(sa.schema.conv('ck_fingerprints_fingerprint_has_owner'), 'host_id IS NOT NULL OR service_id IS NOT NULL')

    with op.batch_alter_table('correlation_runs', schema=None) as batch_op:
        batch_op.alter_column('assets_evaluated', new_column_name='hosts_evaluated', existing_type=sa.Integer())


def _backfill_target_id(bind: sa.engine.Connection) -> None:
    """Resolve ``target_id`` for every pre-existing ``discovered_hosts`` row.

    Imported lazily is unnecessary here (no application-package import at
    all, matching this project's "runnable in isolation" migration
    convention) -- everything needed is a plain SQL join.
    """
    host_rows = bind.execute(
        sa.text("SELECT id, source_execution_id FROM discovered_hosts")
    ).fetchall()

    for host_id, source_execution_id in host_rows:
        target_id = None
        if source_execution_id is not None:
            row = bind.execute(
                sa.text("SELECT target_id FROM tool_executions WHERE id = :execution_id"),
                {"execution_id": source_execution_id},
            ).fetchone()
            if row is not None:
                target_id = row[0]

        if target_id is None:
            # source_execution_id was unset or its execution no longer exists --
            # fall back to this host's earliest recorded execution link.
            row = bind.execute(
                sa.text(
                    "SELECT te.target_id FROM execution_hosts eh "
                    "JOIN tool_executions te ON te.id = eh.execution_id "
                    "WHERE eh.host_id = :host_id ORDER BY eh.created_at ASC LIMIT 1"
                ),
                {"host_id": host_id},
            ).fetchone()
            if row is not None:
                target_id = row[0]

        if target_id is None:
            # No resolvable execution/target history at all -- leave NULL
            # rather than fabricate a target for this legacy row.
            continue

        bind.execute(
            sa.text("UPDATE discovered_hosts SET target_id = :target_id WHERE id = :id"),
            {"target_id": target_id, "id": host_id},
        )


def downgrade() -> None:
    # ### Best-effort only -- see this project's established precedent
    # (d151c8e205d2, f3a9c1d5e7b2) for irreversible/lossy downgrades: the
    # target_id backfill is not undone (nothing depended on its absence),
    # and every rename below is reversed structurally without attempting to
    # reconstruct the pre-migration assessment_id-only merge key. ###
    with op.batch_alter_table('correlation_runs', schema=None) as batch_op:
        batch_op.alter_column('hosts_evaluated', new_column_name='assets_evaluated', existing_type=sa.Integer())

    with op.batch_alter_table('fingerprints', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_fingerprints_host_id'))
        batch_op.drop_constraint(sa.schema.conv('ck_fingerprints_fingerprint_has_owner'), type_='check')
        batch_op.alter_column('host_id', new_column_name='asset_id', existing_type=sa.Uuid())
    with op.batch_alter_table('fingerprints', schema=None) as batch_op:
        batch_op.create_index('ix_fingerprints_asset_id', ['asset_id'], unique=False)
        batch_op.create_check_constraint(sa.schema.conv('ck_fingerprints_fingerprint_has_owner'), 'asset_id IS NOT NULL OR service_id IS NOT NULL')

    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.drop_index('ix_findings_host_id_severity')
        batch_op.drop_index(batch_op.f('ix_findings_host_id'))
        batch_op.alter_column('host_id', new_column_name='asset_id', existing_type=sa.Uuid())
    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.create_index('ix_findings_asset_id', ['asset_id'], unique=False)
        batch_op.create_index('ix_findings_asset_id_severity', ['asset_id', 'severity'], unique=False)

    with op.batch_alter_table('observations', schema=None) as batch_op:
        batch_op.drop_index('uq_observations_host_id_fingerprint')
        batch_op.drop_index(batch_op.f('ix_observations_host_id'))
        batch_op.alter_column('host_id', new_column_name='asset_id', existing_type=sa.Uuid())
    with op.batch_alter_table('observations', schema=None) as batch_op:
        batch_op.create_index('ix_observations_asset_id', ['asset_id'], unique=False)
        batch_op.create_index('uq_observations_asset_id_fingerprint', ['asset_id', 'fingerprint'], unique=True)

    with op.batch_alter_table('network_interfaces', schema=None) as batch_op:
        batch_op.drop_index('uq_network_interfaces_host_id_ip_address')
        batch_op.drop_index(batch_op.f('ix_network_interfaces_host_id'))
        batch_op.alter_column('host_id', new_column_name='asset_id', existing_type=sa.Uuid())
    with op.batch_alter_table('network_interfaces', schema=None) as batch_op:
        batch_op.create_index('ix_network_interfaces_asset_id', ['asset_id'], unique=False)
        batch_op.create_index('uq_network_interfaces_asset_id_ip_address', ['asset_id', 'ip_address'], unique=True)

    with op.batch_alter_table('operating_systems', schema=None) as batch_op:
        batch_op.drop_index('uq_operating_systems_host_id_name_version')
        batch_op.drop_index(batch_op.f('ix_operating_systems_host_id'))
        batch_op.alter_column('host_id', new_column_name='asset_id', existing_type=sa.Uuid())
    with op.batch_alter_table('operating_systems', schema=None) as batch_op:
        batch_op.create_index('ix_operating_systems_asset_id', ['asset_id'], unique=False)
        batch_op.create_index('uq_operating_systems_asset_id_name_version', ['asset_id', 'name', 'version'], unique=True)

    with op.batch_alter_table('technologies', schema=None) as batch_op:
        batch_op.drop_index('uq_technologies_host_id_service_id_name')
        batch_op.drop_index(batch_op.f('ix_technologies_host_id'))
        batch_op.alter_column('host_id', new_column_name='asset_id', existing_type=sa.Uuid())
    with op.batch_alter_table('technologies', schema=None) as batch_op:
        batch_op.create_index('ix_technologies_asset_id', ['asset_id'], unique=False)
        batch_op.create_index('uq_technologies_asset_id_service_id_name', ['asset_id', 'service_id', 'name'], unique=True)

    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.drop_index('uq_services_host_id_fingerprint')
        batch_op.drop_index(batch_op.f('ix_services_host_id'))
        batch_op.alter_column('host_id', new_column_name='asset_id', existing_type=sa.Uuid())
    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.create_index('ix_services_asset_id', ['asset_id'], unique=False)
        batch_op.create_index('uq_services_asset_id_fingerprint', ['asset_id', 'fingerprint'], unique=True)

    with op.batch_alter_table('execution_hosts', schema=None) as batch_op:
        batch_op.drop_index('uq_execution_hosts_execution_id_host_id')
        batch_op.drop_index(batch_op.f('ix_execution_hosts_host_id'))
        batch_op.alter_column('host_id', new_column_name='asset_id', existing_type=sa.Uuid())
    with op.batch_alter_table('execution_hosts', schema=None) as batch_op:
        batch_op.create_index('ix_execution_assets_asset_id', ['asset_id'], unique=False)
        batch_op.create_index('uq_execution_assets_execution_id_asset_id', ['execution_id', 'asset_id'], unique=True)

    with op.batch_alter_table('discovered_hosts', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_discovered_hosts_target_id_targets'), type_='foreignkey')
        batch_op.drop_index('uq_discovered_hosts_target_id_fingerprint')
        batch_op.drop_index(batch_op.f('ix_discovered_hosts_target_id'))
        batch_op.drop_index(batch_op.f('ix_discovered_hosts_source_execution_id'))
        batch_op.drop_index(batch_op.f('ix_discovered_hosts_ipv6'))
        batch_op.drop_index(batch_op.f('ix_discovered_hosts_ipv4'))
        batch_op.drop_index(batch_op.f('ix_discovered_hosts_assessment_id'))
        batch_op.drop_constraint(sa.schema.conv('ck_discovered_hosts_hosttype'), type_='check')
        batch_op.alter_column('host_type', new_column_name='asset_type', existing_type=sa.VARCHAR(length=16))
        batch_op.drop_column('target_id')
    with op.batch_alter_table('discovered_hosts', schema=None) as batch_op:
        batch_op.create_check_constraint(sa.schema.conv('ck_assets_assettype'), "asset_type IN ('HOST', 'WEBSITE', 'API', 'DOMAIN', 'IP')")
        batch_op.create_index('ix_assets_assessment_id', ['assessment_id'], unique=False)
        batch_op.create_index('ix_assets_ipv4', ['ipv4'], unique=False)
        batch_op.create_index('ix_assets_ipv6', ['ipv6'], unique=False)
        batch_op.create_index('ix_assets_source_execution_id', ['source_execution_id'], unique=False)
        batch_op.create_index('uq_assets_assessment_id_fingerprint', ['assessment_id', 'fingerprint'], unique=True)

    op.rename_table('execution_hosts', 'execution_assets')
    op.rename_table('discovered_hosts', 'assets')
