"""The job state machine: which ``ToolExecutionStatus`` transitions are legal.

One authoritative transition table so the manager, the cancel/retry service
methods, and tests all agree on what "cancellable" or "retriable" means,
instead of each re-deriving it from a scattered set of status checks.
"""

from backend.models.enums import ToolExecutionStatus

_S = ToolExecutionStatus

ALLOWED_TRANSITIONS: dict[_S, frozenset[_S]] = {
    _S.PENDING: frozenset({_S.QUEUED, _S.SKIPPED}),
    _S.QUEUED: frozenset({_S.PREPARING, _S.CANCELLED}),
    _S.PREPARING: frozenset({_S.RUNNING, _S.FAILED, _S.CANCELLED}),
    _S.RUNNING: frozenset({_S.COMPLETED, _S.FAILED, _S.CANCELLED, _S.TIMEOUT}),
    _S.COMPLETED: frozenset(),
    _S.FAILED: frozenset({_S.QUEUED}),
    _S.CANCELLED: frozenset({_S.QUEUED}),
    _S.TIMEOUT: frozenset({_S.QUEUED}),
    _S.SKIPPED: frozenset(),
}

#: Jobs actively occupying a queue slot or a worker -- these are the ones ``cancel()`` may act on.
ACTIVE_STATUSES: frozenset[_S] = frozenset({_S.PENDING, _S.QUEUED, _S.PREPARING, _S.RUNNING})

#: Jobs that reached an end state and will never change again without a retry.
TERMINAL_STATUSES: frozenset[_S] = frozenset({_S.COMPLETED, _S.FAILED, _S.CANCELLED, _S.TIMEOUT, _S.SKIPPED})

#: Jobs eligible for ``retry()`` -- a subset of terminal statuses (not COMPLETED or SKIPPED).
RETRIABLE_STATUSES: frozenset[_S] = frozenset({_S.FAILED, _S.CANCELLED, _S.TIMEOUT})


def is_transition_allowed(current: _S, target: _S) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())
