"""Alembic migration environment.

Runs migrations using the application's own async engine configuration
so a single source of truth (``backend.core.config.Settings``) governs
the database URL in both the running app and migrations.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from backend.core.config import get_settings
from backend.database.base import Base

# Importing the models package registers every ORM model on Base.metadata
# so Alembic's autogenerate can detect them.
import backend.models  # noqa: F401,E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection, emitting SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    # render_as_batch: SQLite can't ALTER TABLE directly, so Alembic must
    # rebuild affected tables via a temp-table swap. Harmless on backends
    # (e.g. PostgreSQL) that support ALTER TABLE natively.
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live async database connection."""
    connectable = create_async_engine(settings.database_url, future=True)

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
