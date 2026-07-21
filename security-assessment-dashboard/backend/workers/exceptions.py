"""Execution-engine exception hierarchy.

Deliberately independent of :mod:`backend.core.exceptions` (the FastAPI/HTTP
error hierarchy), mirroring :mod:`backend.plugins.exceptions`'s own
framework-internal hierarchy -- ``backend.services.execution_service``
translates these into the equivalent ``AppException`` subclass at the
service boundary, the same pattern already used for the plugin framework
and DB-not-found errors elsewhere in the codebase.
"""


class ExecutionError(Exception):
    """Base class for all execution-engine exceptions."""


class JobNotFoundError(ExecutionError):
    """Raised when a job id has no matching ``ToolExecution`` row."""


class JobNotCancellableError(ExecutionError):
    """Raised when cancelling a job that is not in an active (cancellable) state."""


class JobNotRetriableError(ExecutionError):
    """Raised when retrying a job that did not end in a retriable (failed/cancelled/timed-out) state."""
