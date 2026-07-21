"""Structured logging configuration.

Configures three separate log streams (application, API access, and
error) as rotating JSON-line log files, in addition to human readable
console output. Call :func:`configure_logging` once during application
startup.
"""

import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.config import Settings


class JsonFormatter(logging.Formatter):
    """Renders log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields:
            payload.update(extra_fields)

        return json.dumps(payload, default=str)


def _make_rotating_handler(path: Path, level: int, formatter: logging.Formatter) -> logging.Handler:
    handler = logging.handlers.RotatingFileHandler(
        filename=path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def configure_logging(settings: Settings) -> None:
    """Configure root, API, and error loggers.

    - ``app.log`` receives all application-level log records.
    - ``api.log`` receives records emitted by the ``api`` logger
      (request/response logging middleware).
    - ``error.log`` receives WARNING and above from every logger.
    """
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = JsonFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    app_handler = _make_rotating_handler(settings.log_dir / "app.log", level, formatter)
    error_handler = _make_rotating_handler(
        settings.log_dir / "error.log", logging.WARNING, formatter
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)

    api_logger = logging.getLogger("api")
    api_logger.setLevel(level)
    api_logger.propagate = True
    api_handler = _make_rotating_handler(settings.log_dir / "api.log", level, formatter)
    api_logger.addHandler(api_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
