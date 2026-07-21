"""Async database engine and session management.

Provides a process-wide async engine/sessionmaker pair built from the
application's :class:`~backend.core.config.Settings`, plus a FastAPI
dependency for acquiring a scoped session. No ORM models are registered
yet; this module only establishes the connection infrastructure that
later phases will build on.
"""

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import Settings, get_settings


def _enable_sqlite_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    """Turn on SQLite foreign-key enforcement for a new DBAPI connection.

    SQLite ignores ``FOREIGN KEY`` constraints unless this pragma is set on
    every connection, so ``ON DELETE CASCADE``/``RESTRICT`` rules declared
    on the ORM models would otherwise silently do nothing.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _enable_sqlite_wal_mode(dbapi_connection: object, _connection_record: object) -> None:
    """Switch SQLite to WAL journal mode on every new DBAPI connection.

    Every phase through Phase 5 only ever had one writer at a time (one HTTP
    request, handled sequentially). Phase 6's execution engine is the first
    thing to give this single SQLite file genuine concurrent writers -- job
    worker tasks, the HTTP request session, and the cancellation safety-net
    task can all be mid-transaction at once -- while the frontend's 1.5s
    polling adds frequent concurrent readers on top of that. SQLite's default
    rollback-journal mode makes readers and writers block each other, so
    under this new concurrent load that combination reliably produced
    ``sqlite3.OperationalError: database is locked`` (observed directly:
    minutes-long stalls even with a raised busy-timeout, not just an
    occasional collision). WAL mode lets readers proceed concurrently with a
    single writer instead of serializing everything -- the standard fix for
    SQLite under concurrent asyncio access, and a database-level setting
    that persists in the file itself once set.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def create_engine(settings: Settings) -> AsyncEngine:
    """Create the async SQLAlchemy engine for the configured database URL.

    SQLite's own default busy-timeout (5s, set by the stdlib ``sqlite3``
    module) is too short now that the execution engine (Phase 6) gives this
    single SQLite file real concurrent writers -- job workers, the HTTP
    request session, and the cancellation safety-net task can all commit
    around the same moment. Without a longer timeout, one connection's
    ``COMMIT`` can lose the race for the write lock and raise
    ``sqlite3.OperationalError: database is locked`` instead of simply
    waiting its turn (observed directly while testing job cancellation).
    30s is comfortably longer than any single commit in this codebase takes.
    """
    connect_args = {"timeout": 30} if settings.database_url.startswith("sqlite") else {}
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )
    if engine.dialect.name == "sqlite":
        event.listen(engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
        event.listen(engine.sync_engine, "connect", _enable_sqlite_wal_mode)
    return engine


_engine: AsyncEngine = create_engine(get_settings())
_session_factory = async_sessionmaker(
    bind=_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a scoped async database session.

    Commits once at the end of a successful request and rolls back on any
    exception, so a request handler is one transaction: a service can call
    several repository methods and have them all succeed or fail together,
    per the transaction-boundary design established in the repository layer.
    """
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def background_session() -> AsyncIterator[AsyncSession]:
    """Async context manager yielding a session for code outside a request lifecycle.

    ``backend.workers.manager.ExecutionManager`` runs job workers as
    long-lived ``asyncio`` tasks with no FastAPI request to scope a
    session to (a job routinely outlives the HTTP request that queued
    it) -- this gives that background code the same commit-on-success/
    rollback-on-exception unit-of-work semantics as :func:`get_db_session`.
    """
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the engine's connection pool. Call on application shutdown."""
    await _engine.dispose()
