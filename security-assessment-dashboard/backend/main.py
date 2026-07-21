"""Application entrypoint: FastAPI app factory and ASGI instance.

Run locally with:

    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.middleware.logging_middleware import RequestLoggingMiddleware
from backend.api.routes import api_router
from backend.core.config import get_settings
from backend.core.exceptions import register_exception_handlers
from backend.core.logging import configure_logging
from backend.core.security import is_secret_key_weak
from backend.database.session import dispose_engine
from backend.plugins.manager.plugin_manager import get_plugin_manager
from backend.workers.manager import shutdown_execution_manager

settings = get_settings()
configure_logging(settings)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown."""
    app.state.start_time = time.monotonic()

    if is_secret_key_weak(settings.secret_key):
        logger.warning(
            "SECRET_KEY is missing, short, or a known default. "
            "Set a strong SECRET_KEY before deploying to production."
        )

    logger.info(
        "%s v%s starting in %s mode",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )

    plugin_manager = get_plugin_manager(settings.plugins_dir)
    failures = plugin_manager.discovery_failures()
    logger.info(
        "Plugin discovery: %d registered, %d failed",
        len(plugin_manager.list_plugins()),
        len(failures),
    )
    for failure in failures:
        logger.warning("Plugin at '%s' failed to load: %s", failure.directory, failure.error)

    yield

    await shutdown_execution_manager()
    await dispose_engine()
    logger.info("%s shutting down", settings.app_name)


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()
