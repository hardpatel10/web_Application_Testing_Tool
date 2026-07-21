"""Structured application exceptions and global exception handlers.

All application-raised errors should derive from :class:`AppException` so
that they carry a stable machine-readable ``error_code`` alongside the
HTTP status and human-readable message. This keeps error handling
consistent as the number of routes and services grows.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base class for all structured, application-raised exceptions."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "APP_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(
            message, error_code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND
        )


class ServiceUnavailableError(AppException):
    def __init__(self, message: str = "Service unavailable") -> None:
        super().__init__(
            message,
            error_code="SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class ConflictError(AppException):
    """Raised when a request would violate a uniqueness rule (e.g. duplicate name)."""

    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message, error_code="CONFLICT", status_code=status.HTTP_409_CONFLICT)


class InvalidInputError(AppException):
    """Raised for business-rule input validation failures (e.g. an invalid target value).

    Distinct from FastAPI/Pydantic's automatic request-shape validation
    (handled by ``RequestValidationError`` below) — this is for values that
    are shaped correctly but semantically invalid.
    """

    def __init__(self, message: str = "Invalid input") -> None:
        super().__init__(message, error_code="INVALID_INPUT", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


def _error_response(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI application."""

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Application exception: %s", exc.message, extra={"extra_fields": {"path": str(request.url)}}
        )
        return _error_response(exc.status_code, exc.error_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info(
            "Request validation failed", extra={"extra_fields": {"errors": exc.errors(), "path": str(request.url)}}
        )
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Request validation failed.",
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return _error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception on %s", request.url, exc_info=exc
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred.",
        )
