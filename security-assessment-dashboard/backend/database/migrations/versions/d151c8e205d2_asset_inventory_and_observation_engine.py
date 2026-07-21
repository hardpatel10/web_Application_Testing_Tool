"""asset_inventory_and_observation_engine

Revision ID: d151c8e205d2
Revises: 63098bf45bce
Create Date: 2026-07-19 12:18:36.113182

Phase 8: restructures ``assets``/``services``/``observations`` from
per-execution snapshots into a durable, deduplicated inventory, and adds
seven new tables (``network_interfaces``, ``technologies``,
``operating_systems``, ``observation_evidence``, ``fingerprints``,
``execution_assets``, ``execution_observations``).

This is a real data migration, not just a schema change -- unlike every
prior migration in this project, there is pre-existing data on the line
(real Nmap scans from Phases 6/7 testing). ``upgrade()`` is staged in three
passes specifically to make that safe:

1. Add every new column as *nullable*, with no new NOT NULL constraints,
   no new unique indexes, and old columns/indexes/FKs left untouched.
2. ``_backfill_existing_data()``: a Python-driven pass (not one giant SQL
   statement, to stay debuggable) that computes each existing row's
   deterministic fingerprint via the same ``backend.services.fingerprinting``
   functions the application itself uses, splits ``ip_address`` into
   ``ipv4``/``ipv6``, backfills ``assessment_id`` via the ``execution_id`` ->
   ``tool_executions.assessment_id`` join, and inserts one
   ``ExecutionAsset``/``ExecutionObservation`` row per existing asset/
   observation (``is_new=True`` -- from the system's perspective, each was
   first discovered by its one recorded execution).
3. Tighten the new columns to NOT NULL, add the new unique indexes/FKs, and
   drop the old ``assets.execution_id``/``ip_address``/``os_name``/
   ``os_accuracy`` columns (fully superseded).

Enum columns in this codebase store the Python ``Enum`` member's *name*
(e.g. ``'HOST'``, ``'TCP'``), not its ``.value`` -- confirmed directly
against this project's live dev database before writing the backfill
below (every existing enum column, e.g. ``services.protocol``, stores
``'TCP'``, not ``'tcp'``).

``downgrade()`` reverses the brand-new tables and the additive nullable
columns cleanly, but -- like every prior migration's documented SQLite
batch-mode limitation (see Phase 3/5/7's own migrations) -- does not
attempt to un-backfill or restore the dropped ``assets.execution_id``/
``ip_address``/``os_name``/``os_accuracy`` data; ``upgrade()`` is the
fully verified path.
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd151c8e205d2'
down_revision: Union[str, None] = '63098bf45bce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Pass 1: brand new tables (no data concerns) ---------------------------
    op.create_table('execution_assets',
    sa.Column('execution_id', sa.Uuid(), nullable=False),
    sa.Column('asset_id', sa.Uuid(), nullable=False),
    sa.Column('is_new', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], name=op.f('fk_execution_assets_asset_id_assets'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['execution_id'], ['tool_executions.id'], name=op.f('fk_execution_assets_execution_id_tool_executions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_execution_assets'))
    )
    with op.batch_alter_table('execution_assets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_execution_assets_asset_id'), ['asset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_execution_assets_execution_id'), ['execution_id'], unique=False)
        batch_op.create_index('uq_execution_assets_execution_id_asset_id', ['execution_id', 'asset_id'], unique=True)

    op.create_table('network_interfaces',
    sa.Column('asset_id', sa.Uuid(), nullable=False),
    sa.Column('ip_address', sa.String(length=45), nullable=False),
    sa.Column('version', sa.Enum('IPV4', 'IPV6', 'CIDR', 'HOSTNAME', 'DOMAIN', 'URL', name='targettype', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('mac_address', sa.String(length=17), nullable=True),
    sa.Column('network', sa.String(length=64), nullable=True),
    sa.Column('interface_name', sa.String(length=64), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], name=op.f('fk_network_interfaces_asset_id_assets'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_network_interfaces'))
    )
    with op.batch_alter_table('network_interfaces', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_network_interfaces_asset_id'), ['asset_id'], unique=False)
        batch_op.create_index('uq_network_interfaces_asset_id_ip_address', ['asset_id', 'ip_address'], unique=True)

    op.create_table('operating_systems',
    sa.Column('asset_id', sa.Uuid(), nullable=False),
    sa.Column('vendor', sa.String(length=255), nullable=True),
    sa.Column('family', sa.String(length=255), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('version', sa.String(length=100), nullable=True),
    sa.Column('accuracy', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=100), nullable=False),
    sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
    sa.Column('source_execution_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], name=op.f('fk_operating_systems_asset_id_assets'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_execution_id'], ['tool_executions.id'], name=op.f('fk_operating_systems_source_execution_id_tool_executions'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_operating_systems'))
    )
    with op.batch_alter_table('operating_systems', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_operating_systems_asset_id'), ['asset_id'], unique=False)
        batch_op.create_index('uq_operating_systems_asset_id_name_version', ['asset_id', 'name', 'version'], unique=True)

    op.create_table('fingerprints',
    sa.Column('asset_id', sa.Uuid(), nullable=True),
    sa.Column('service_id', sa.Uuid(), nullable=True),
    sa.Column('fingerprint_type', sa.Enum('SSH', 'TLS', 'HTTP', 'SMB', 'BANNER', 'HASH', name='fingerprinttype', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('source_execution_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('asset_id IS NOT NULL OR service_id IS NOT NULL', name=op.f('ck_fingerprints_fingerprint_has_owner')),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], name=op.f('fk_fingerprints_asset_id_assets'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], name=op.f('fk_fingerprints_service_id_services'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_execution_id'], ['tool_executions.id'], name=op.f('fk_fingerprints_source_execution_id_tool_executions'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fingerprints'))
    )
    with op.batch_alter_table('fingerprints', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_fingerprints_asset_id'), ['asset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_fingerprints_service_id'), ['service_id'], unique=False)

    op.create_table('technologies',
    sa.Column('asset_id', sa.Uuid(), nullable=False),
    sa.Column('service_id', sa.Uuid(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('vendor', sa.String(length=255), nullable=True),
    sa.Column('version', sa.String(length=100), nullable=True),
    sa.Column('category', sa.Enum('WEB_SERVER', 'DATABASE', 'LANGUAGE', 'FRAMEWORK', 'MIDDLEWARE', 'OPERATING_SYSTEM', 'OTHER', name='technologycategory', native_enum=False, create_constraint=True, length=24), nullable=False),
    sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
    sa.Column('source_execution_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], name=op.f('fk_technologies_asset_id_assets'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], name=op.f('fk_technologies_service_id_services'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_execution_id'], ['tool_executions.id'], name=op.f('fk_technologies_source_execution_id_tool_executions'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_technologies'))
    )
    with op.batch_alter_table('technologies', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_technologies_asset_id'), ['asset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_technologies_service_id'), ['service_id'], unique=False)
        batch_op.create_index('uq_technologies_asset_id_service_id_name', ['asset_id', 'service_id', 'name'], unique=True)

    op.create_table('execution_observations',
    sa.Column('execution_id', sa.Uuid(), nullable=False),
    sa.Column('observation_id', sa.Uuid(), nullable=False),
    sa.Column('is_new', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['execution_id'], ['tool_executions.id'], name=op.f('fk_execution_observations_execution_id_tool_executions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['observation_id'], ['observations.id'], name=op.f('fk_execution_observations_observation_id_observations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_execution_observations'))
    )
    with op.batch_alter_table('execution_observations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_execution_observations_execution_id'), ['execution_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_execution_observations_observation_id'), ['observation_id'], unique=False)
        batch_op.create_index('uq_execution_observations_execution_id_observation_id', ['execution_id', 'observation_id'], unique=True)

    op.create_table('observation_evidence',
    sa.Column('observation_id', sa.Uuid(), nullable=False),
    sa.Column('source_tool', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('file_path', sa.String(length=1024), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['observation_id'], ['observations.id'], name=op.f('fk_observation_evidence_observation_id_observations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_observation_evidence'))
    )
    with op.batch_alter_table('observation_evidence', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_observation_evidence_observation_id'), ['observation_id'], unique=False)

    # -- Pass 2: additive *nullable* columns on the restructured tables --------
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assessment_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('fqdn', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('ipv4', sa.String(length=15), nullable=True))
        batch_op.add_column(sa.Column('ipv6', sa.String(length=45), nullable=True))
        batch_op.add_column(sa.Column('asset_type', sa.Enum('HOST', 'WEBSITE', 'API', 'DOMAIN', 'IP', name='assettype', native_enum=False, create_constraint=True, length=16), nullable=True))
        batch_op.add_column(sa.Column('fingerprint', sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('source_execution_id', sa.Uuid(), nullable=True))

    with op.batch_alter_table('observations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('service_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('plugin', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('category', sa.Enum('NETWORK', 'WEB', 'TLS', 'AUTH', 'CONFIGURATION', 'OS', 'OTHER', name='observationcategory', native_enum=False, create_constraint=True, length=16), nullable=True))
        batch_op.add_column(sa.Column('observation_type', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('fingerprint', sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column('execution_id', existing_type=sa.CHAR(length=32), nullable=True)

    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vendor', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('banner', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('fingerprint', sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True))

    # -- Pass 3: backfill every existing row -------------------------------------
    _backfill_existing_data(op.get_bind())

    # -- Pass 4: tighten to NOT NULL, add unique indexes/FKs, drop old columns --
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.alter_column('assessment_id', existing_type=sa.Uuid(), nullable=False)
        batch_op.alter_column('asset_type', existing_type=sa.Enum('HOST', 'WEBSITE', 'API', 'DOMAIN', 'IP', name='assettype', native_enum=False, create_constraint=True, length=16), nullable=False)
        batch_op.alter_column('fingerprint', existing_type=sa.String(length=80), nullable=False)
        batch_op.alter_column('first_seen', existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.alter_column('last_seen', existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.drop_index('ix_assets_execution_id')
        batch_op.drop_index('ix_assets_ip_address')
        batch_op.create_index(batch_op.f('ix_assets_assessment_id'), ['assessment_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_assets_ipv4'), ['ipv4'], unique=False)
        batch_op.create_index(batch_op.f('ix_assets_ipv6'), ['ipv6'], unique=False)
        batch_op.create_index(batch_op.f('ix_assets_source_execution_id'), ['source_execution_id'], unique=False)
        batch_op.create_index('uq_assets_assessment_id_fingerprint', ['assessment_id', 'fingerprint'], unique=True)
        batch_op.drop_constraint('fk_assets_execution_id_tool_executions', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_assets_source_execution_id_tool_executions'), 'tool_executions', ['source_execution_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key(batch_op.f('fk_assets_assessment_id_assessments'), 'assessments', ['assessment_id'], ['id'], ondelete='CASCADE')
        batch_op.drop_column('execution_id')
        batch_op.drop_column('ip_address')
        batch_op.drop_column('os_name')
        batch_op.drop_column('os_accuracy')

    with op.batch_alter_table('observations', schema=None) as batch_op:
        batch_op.alter_column('category', existing_type=sa.Enum('NETWORK', 'WEB', 'TLS', 'AUTH', 'CONFIGURATION', 'OS', 'OTHER', name='observationcategory', native_enum=False, create_constraint=True, length=16), nullable=False)
        batch_op.alter_column('fingerprint', existing_type=sa.String(length=80), nullable=False)
        batch_op.alter_column('first_seen', existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.alter_column('last_seen', existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.create_index(batch_op.f('ix_observations_plugin'), ['plugin'], unique=False)
        batch_op.create_index(batch_op.f('ix_observations_service_id'), ['service_id'], unique=False)
        batch_op.create_index('uq_observations_asset_id_fingerprint', ['asset_id', 'fingerprint'], unique=True)
        batch_op.drop_constraint('fk_observations_execution_id_tool_executions', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_observations_service_id_services'), 'services', ['service_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_observations_execution_id_tool_executions'), 'tool_executions', ['execution_id'], ['id'], ondelete='SET NULL')

    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.alter_column('fingerprint', existing_type=sa.String(length=80), nullable=False)
        batch_op.alter_column('first_seen', existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.alter_column('last_seen', existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.create_index('uq_services_asset_id_fingerprint', ['asset_id', 'fingerprint'], unique=True)


def _backfill_existing_data(bind: sa.engine.Connection) -> None:
    """Populate every new column on pre-existing ``assets``/``services``/``observations`` rows.

    Imported lazily (inside the function, not at module scope) so this
    migration file has no import-time dependency on the application
    package layout -- consistent with keeping Alembic revisions runnable
    in isolation.
    """
    from backend.models.enums import NetworkProtocol
    from backend.services import fingerprinting

    # -- Assets: backfill assessment_id, ipv4/ipv6, fingerprint, first/last_seen --
    asset_rows = bind.execute(
        sa.text("SELECT id, execution_id, ip_address, hostname, mac_address, created_at FROM assets")
    ).fetchall()

    asset_fingerprints: dict[str, str] = {}  # asset_id (hex) -> fingerprint, needed by the services pass below

    for asset_id, execution_id, ip_address, hostname, mac_address, created_at in asset_rows:
        assessment_row = bind.execute(
            sa.text("SELECT assessment_id FROM tool_executions WHERE id = :execution_id"),
            {"execution_id": execution_id},
        ).fetchone()
        if assessment_row is None:
            # Orphaned row (its execution was hard-deleted somehow) -- cannot
            # be scoped to an assessment at all; skip rather than guess.
            continue
        assessment_id = assessment_row[0]

        ipv4 = ip_address if ip_address and _is_ipv4(ip_address) else None
        ipv6 = ip_address if ip_address and not _is_ipv4(ip_address) else None

        try:
            fingerprint = fingerprinting.asset_fingerprint(
                mac_address=mac_address, ipv4=ipv4, ipv6=ipv6, hostname=hostname
            )
        except ValueError:
            # No identity signal at all on this pre-existing row (shouldn't
            # happen in practice) -- fall back to the row's own id so the
            # NOT NULL + uniqueness pass below never fails.
            fingerprint = f"legacy:{asset_id}"

        asset_fingerprints[asset_id] = fingerprint

        bind.execute(
            sa.text(
                "UPDATE assets SET assessment_id = :assessment_id, ipv4 = :ipv4, ipv6 = :ipv6, "
                "asset_type = 'HOST', fingerprint = :fingerprint, first_seen = :created_at, "
                "last_seen = :created_at, source_execution_id = :execution_id WHERE id = :id"
            ),
            {
                "assessment_id": assessment_id, "ipv4": ipv4, "ipv6": ipv6, "fingerprint": fingerprint,
                "created_at": created_at, "execution_id": execution_id, "id": asset_id,
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO execution_assets (id, execution_id, asset_id, is_new, created_at) "
                "VALUES (:id, :execution_id, :asset_id, 1, :created_at)"
            ),
            {"id": uuid.uuid4().hex, "execution_id": execution_id, "asset_id": asset_id, "created_at": created_at},
        )

    # -- Services: backfill fingerprint, first/last_seen (needs each asset's fingerprint above) --
    service_rows = bind.execute(
        sa.text("SELECT id, asset_id, port, protocol, created_at FROM services")
    ).fetchall()

    for service_id, asset_id, port, protocol_name, created_at in service_rows:
        asset_fp = asset_fingerprints.get(asset_id)
        if asset_fp is None:
            continue  # asset row was skipped above (orphaned execution) -- nothing to scope this service to
        protocol = NetworkProtocol[protocol_name]
        fingerprint = fingerprinting.service_fingerprint(asset_fingerprint_value=asset_fp, port=port, protocol=protocol)
        bind.execute(
            sa.text(
                "UPDATE services SET fingerprint = :fingerprint, first_seen = :created_at, last_seen = :created_at WHERE id = :id"
            ),
            {"fingerprint": fingerprint, "created_at": created_at, "id": service_id},
        )

    # -- Observations: backfill plugin, category, fingerprint, first/last_seen --
    observation_rows = bind.execute(
        sa.text("SELECT id, execution_id, asset_id, source, title, detail, created_at FROM observations")
    ).fetchall()

    for observation_id, execution_id, asset_id, source, title, detail, created_at in observation_rows:
        plugin_row = bind.execute(
            sa.text(
                "SELECT tools.name FROM tool_executions "
                "JOIN tools ON tools.id = tool_executions.tool_id "
                "WHERE tool_executions.id = :execution_id"
            ),
            {"execution_id": execution_id},
        ).fetchone()
        plugin_name = plugin_row[0] if plugin_row else "unknown"

        asset_fp = asset_fingerprints.get(asset_id) if asset_id else None
        fingerprint = fingerprinting.observation_fingerprint(
            plugin=plugin_name, asset_fingerprint_value=asset_fp or "none", category="other",
            observation_type=None, title=title,
        )

        bind.execute(
            sa.text(
                "UPDATE observations SET plugin = :plugin, category = 'OTHER', fingerprint = :fingerprint, "
                "first_seen = :created_at, last_seen = :created_at WHERE id = :id"
            ),
            {"plugin": plugin_name, "fingerprint": fingerprint, "created_at": created_at, "id": observation_id},
        )
        bind.execute(
            sa.text(
                "INSERT INTO execution_observations (id, execution_id, observation_id, is_new, created_at) "
                "VALUES (:id, :execution_id, :observation_id, 1, :created_at)"
            ),
            {"id": uuid.uuid4().hex, "execution_id": execution_id, "observation_id": observation_id, "created_at": created_at},
        )
        bind.execute(
            sa.text(
                "INSERT INTO observation_evidence (id, observation_id, source_tool, title, content, created_at) "
                "VALUES (:id, :observation_id, :plugin, :title, :content, :created_at)"
            ),
            {
                "id": uuid.uuid4().hex, "observation_id": observation_id, "plugin": plugin_name,
                "title": source, "content": detail, "created_at": created_at,
            },
        )


def _is_ipv4(value: str) -> bool:
    import ipaddress

    try:
        ipaddress.IPv4Address(value)
        return True
    except ValueError:
        return False


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.drop_index('uq_services_asset_id_fingerprint')
        batch_op.drop_column('last_seen')
        batch_op.drop_column('first_seen')
        batch_op.drop_column('fingerprint')
        batch_op.drop_column('banner')
        batch_op.drop_column('vendor')

    with op.batch_alter_table('observations', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_observations_execution_id_tool_executions'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_observations_service_id_services'), type_='foreignkey')
        batch_op.create_foreign_key('fk_observations_execution_id_tool_executions', 'tool_executions', ['execution_id'], ['id'], ondelete='CASCADE')
        batch_op.drop_index('uq_observations_asset_id_fingerprint')
        batch_op.drop_index(batch_op.f('ix_observations_service_id'))
        batch_op.drop_index(batch_op.f('ix_observations_plugin'))
        batch_op.alter_column('execution_id',
               existing_type=sa.CHAR(length=32),
               nullable=False)
        batch_op.drop_column('last_seen')
        batch_op.drop_column('first_seen')
        batch_op.drop_column('fingerprint')
        batch_op.drop_column('observation_type')
        # NOTE: `category` is deliberately NOT dropped here. SQLAlchemy's
        # Enum(create_constraint=True) ties its CHECK constraint to the
        # column in a way batch mode's table-recreate keeps re-emitting even
        # after an explicit drop_constraint() -- a known, narrow SQLite+
        # Alembic interaction, not a data-loss risk (the column is left
        # behind, nullable, unused once downgraded). Matches this project's
        # established "documented SQLite batch-mode downgrade limitation,
        # upgrade() is the fully verified path" precedent from Phases 3/5/7.
        batch_op.drop_column('plugin')
        batch_op.drop_column('service_id')

    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('os_accuracy', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('os_name', sa.VARCHAR(length=255), nullable=True))
        batch_op.add_column(sa.Column('ip_address', sa.VARCHAR(length=45), nullable=True))
        batch_op.add_column(sa.Column('execution_id', sa.CHAR(length=32), nullable=True))
        batch_op.drop_constraint(batch_op.f('fk_assets_assessment_id_assessments'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_assets_source_execution_id_tool_executions'), type_='foreignkey')
        batch_op.create_foreign_key('fk_assets_execution_id_tool_executions', 'tool_executions', ['execution_id'], ['id'], ondelete='CASCADE')
        batch_op.drop_index('uq_assets_assessment_id_fingerprint')
        batch_op.drop_index(batch_op.f('ix_assets_source_execution_id'))
        batch_op.drop_index(batch_op.f('ix_assets_ipv6'))
        batch_op.drop_index(batch_op.f('ix_assets_ipv4'))
        batch_op.drop_index(batch_op.f('ix_assets_assessment_id'))
        batch_op.create_index('ix_assets_ip_address', ['ip_address'], unique=False)
        batch_op.create_index('ix_assets_execution_id', ['execution_id'], unique=False)
        batch_op.drop_column('source_execution_id')
        batch_op.drop_column('last_seen')
        batch_op.drop_column('first_seen')
        batch_op.drop_column('fingerprint')
        # NOTE: `asset_type` is deliberately NOT dropped here -- see the
        # matching comment in the observations block above (same Alembic/
        # SQLite batch-mode CHECK-constraint limitation for enum columns).
        batch_op.drop_column('ipv6')
        batch_op.drop_column('ipv4')
        batch_op.drop_column('fqdn')
        batch_op.drop_column('assessment_id')
    # NOTE: execution_id is left nullable on downgrade (Phase 8's assets no
    # longer track which single execution "owns" them, so there is no source
    # to backfill it from) -- a documented, deliberate divergence from the
    # pre-Phase-8 schema, same class of limitation as every prior migration's
    # SQLite batch-mode downgrade note. upgrade() is the fully verified path.

    with op.batch_alter_table('observation_evidence', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_observation_evidence_observation_id'))

    op.drop_table('observation_evidence')
    with op.batch_alter_table('execution_observations', schema=None) as batch_op:
        batch_op.drop_index('uq_execution_observations_execution_id_observation_id')
        batch_op.drop_index(batch_op.f('ix_execution_observations_observation_id'))
        batch_op.drop_index(batch_op.f('ix_execution_observations_execution_id'))

    op.drop_table('execution_observations')
    with op.batch_alter_table('technologies', schema=None) as batch_op:
        batch_op.drop_index('uq_technologies_asset_id_service_id_name')
        batch_op.drop_index(batch_op.f('ix_technologies_service_id'))
        batch_op.drop_index(batch_op.f('ix_technologies_asset_id'))

    op.drop_table('technologies')
    with op.batch_alter_table('fingerprints', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_fingerprints_service_id'))
        batch_op.drop_index(batch_op.f('ix_fingerprints_asset_id'))

    op.drop_table('fingerprints')
    with op.batch_alter_table('operating_systems', schema=None) as batch_op:
        batch_op.drop_index('uq_operating_systems_asset_id_name_version')
        batch_op.drop_index(batch_op.f('ix_operating_systems_asset_id'))

    op.drop_table('operating_systems')
    with op.batch_alter_table('network_interfaces', schema=None) as batch_op:
        batch_op.drop_index('uq_network_interfaces_asset_id_ip_address')
        batch_op.drop_index(batch_op.f('ix_network_interfaces_asset_id'))

    op.drop_table('network_interfaces')
    with op.batch_alter_table('execution_assets', schema=None) as batch_op:
        batch_op.drop_index('uq_execution_assets_execution_id_asset_id')
        batch_op.drop_index(batch_op.f('ix_execution_assets_execution_id'))
        batch_op.drop_index(batch_op.f('ix_execution_assets_asset_id'))

    op.drop_table('execution_assets')
    # ### end Alembic commands ###
