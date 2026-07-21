"""Shared pytest fixtures for the backend test suite.

Points the app at an isolated, throwaway SQLite database and assessment
directory root — set as environment variables *before* any ``backend.*``
module is imported, since ``Settings`` is process-wide and cached
(``@lru_cache``) and the database engine is bound to it at import time.
Tests therefore exercise the real database/filesystem layers (per
``CLAUDE.md``'s "no mocking" rule) without touching the developer's real
``data/app.db`` or ``data/assessments/``.
"""

import os
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

_TEST_DATA_DIR = Path(__file__).resolve().parent / "test_data"
_TEST_DB_PATH = _TEST_DATA_DIR / "test_app.db"
_TEST_ASSESSMENT_ROOT = _TEST_DATA_DIR / "assessments"

if _TEST_DATA_DIR.exists():
    shutil.rmtree(_TEST_DATA_DIR)
_TEST_DATA_DIR.mkdir(parents=True)

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ["ASSESSMENT_ROOT_DIR"] = str(_TEST_ASSESSMENT_ROOT)

import asyncio  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

import backend.models  # noqa: E402,F401  registers all models on Base.metadata
from backend.database.base import Base  # noqa: E402
from backend.database.session import _engine  # noqa: E402
from backend.main import app  # noqa: E402


async def _create_schema() -> None:
    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


# Run once at collection time (a plain module-level call, not a pytest-asyncio
# fixture) so it never has to negotiate event-loop scope with pytest-asyncio's
# per-test event loop — schema setup happens before any test's loop exists.
asyncio.run(_create_schema())


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """An async HTTP client bound to the FastAPI app via ASGI transport.

    Drives the app's lifespan manually so startup state (e.g. ``start_time``)
    is populated, since ASGITransport does not trigger lifespan events on its own.
    """
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
    # `_engine` is a module-level singleton (see backend.database.session)
    # reused across every test, while each test function gets its own fresh
    # event loop (`asyncio_default_fixture_loop_scope = function`). Without
    # disposing it here, a connection checked back into the pool at the end
    # of this test can get handed to the *next* test's session on a
    # different loop -- and aiosqlite's background worker thread for that
    # connection still holds a reference to the loop it was opened on, so a
    # later callback can land on an already-closed loop
    # (``RuntimeError: Event loop is closed``, surfaced as a
    # ``PytestUnhandledThreadExceptionWarning``, observed directly while
    # testing Phase 6's execution engine -- the first thing in this codebase
    # to do genuine DB work outside a request/response cycle, so pooled
    # connections can now still be finishing up right as a test ends).
    # Disposing forces every connection to be freshly opened on whichever
    # loop next uses it, per SQLAlchemy's own guidance for async engines
    # exercised across multiple event loops in a test suite.
    await _engine.dispose()
