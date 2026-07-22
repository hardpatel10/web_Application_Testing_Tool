"""``PipelineRule``: the interface every rule in :mod:`backend.pipeline.rules` implements.

Mirrors :class:`backend.correlation.base.CorrelationRule`'s shape (class-level
metadata + one pure evaluation method) deliberately -- this codebase already
has a well-tested convention for "a self-describing unit with fixed metadata
plus one evaluation method," reused here rather than inventing a second one.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from backend.models.discovered_host import DiscoveredHost
from backend.models.service import Service
from backend.pipeline.models import PipelineDecision


class PipelineRule(ABC):
    """One deterministic rule deciding what, if anything, to do about one discovered service."""

    rule_id: ClassVar[str]
    description: ClassVar[str]

    @abstractmethod
    def evaluate(self, service: Service, host: DiscoveredHost) -> PipelineDecision:
        """Return this rule's verdict on ``service``, or ``None`` if it doesn't recognize it.

        Must be a pure function of ``service``/``host`` -- no I/O, no
        randomness, no clock reads. Returning ``None`` means "not my
        concern," distinct from a :class:`~backend.pipeline.models.SkipDecision`
        (which means "recognized, and deliberately not scanning it") --
        both are real, different answers.
        """
        raise NotImplementedError
