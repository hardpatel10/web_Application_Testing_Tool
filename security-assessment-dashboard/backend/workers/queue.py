"""ExecutionQueue: ordering, cancellation-before-start, and retry priority.

Pure in-memory bookkeeping over job ids -- no plugin or database access,
matching ``backend.plugins.registry.PluginRegistry``'s own "pure
bookkeeping" scope. ``backend.workers.manager.ExecutionManager`` is the
only consumer. Built on ``asyncio.PriorityQueue`` (never a process pool or
external broker) so ``dequeue()`` can await the next job without a
polling loop.
"""

import asyncio
import itertools
import uuid
from dataclasses import dataclass, field

#: Freshly planned jobs queue behind this; retries use a lower number so they jump ahead.
DEFAULT_PRIORITY = 100
RETRY_PRIORITY = 0


@dataclass(order=True)
class _QueueEntry:
    sort_key: tuple[int, int]
    job_id: uuid.UUID = field(compare=False)


class ExecutionQueue:
    """A priority-ordered (lower first), FIFO-within-priority queue of pending job ids."""

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[_QueueEntry] = asyncio.PriorityQueue()
        self._cancelled: set[uuid.UUID] = set()
        self._sequence = itertools.count()

    async def enqueue(self, job_id: uuid.UUID, *, priority: int = DEFAULT_PRIORITY) -> None:
        self._cancelled.discard(job_id)
        await self._queue.put(_QueueEntry((priority, next(self._sequence)), job_id))

    async def dequeue(self) -> uuid.UUID:
        """Return the next job id to run, silently skipping any cancelled before they were dequeued."""
        while True:
            entry = await self._queue.get()
            if entry.job_id in self._cancelled:
                self._cancelled.discard(entry.job_id)
                continue
            return entry.job_id

    def cancel_queued(self, job_id: uuid.UUID) -> None:
        """Mark a not-yet-dequeued job as cancelled so ``dequeue()`` skips it once popped."""
        self._cancelled.add(job_id)

    def qsize(self) -> int:
        return self._queue.qsize()
