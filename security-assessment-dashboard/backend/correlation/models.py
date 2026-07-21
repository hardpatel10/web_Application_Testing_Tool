"""Pure, DB-session-free shapes exchanged between the Correlation Engine and its rules.

A rule receives a :class:`RuleContext` (everything currently known about one
host) and returns zero or more :class:`FindingCandidate`\\ s. Neither type
touches the database or an ``AsyncSession`` — :mod:`backend.services.correlation_service`
is the only place a candidate becomes a persisted ``Finding`` row, mirroring
the split between :mod:`backend.plugins.models.normalized` (pure data) and
:mod:`backend.services.host_inventory_service` (the persistence layer) from
Phase 7/8.
"""

from dataclasses import dataclass, field

from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import FindingReferenceType
from backend.models.observation import Observation
from backend.models.operating_system import OperatingSystem
from backend.models.service import Service
from backend.models.technology import Technology


@dataclass(frozen=True, slots=True)
class RuleReference:
    """One real, static external reference a rule cites -- never a rule-invented id."""

    reference_type: FindingReferenceType
    value: str


@dataclass(slots=True)
class RuleContext:
    """Everything currently known about one host, for one rule's :meth:`~backend.correlation.base.CorrelationRule.evaluate` call."""

    host: DiscoveredHost
    services: list[Service]
    technologies: list[Technology]
    operating_systems: list[OperatingSystem]
    observations: list[Observation]


@dataclass(slots=True)
class FindingCandidate:
    """One rule match: the evidence-backed conclusion a rule drew from its ``RuleContext``.

    ``detail``/``evidence_title`` become the finding's ``description`` and
    its first ``FindingEvidence`` row; ``matched_*`` lists are exactly the
    "Evidence Requirements" / "all observation references" the phase brief
    asks the engine to maintain -- every fact this specific match relied on,
    for the Correlation Engine to persist and for the Finding Details page
    to display back to the analyst.
    """

    detail: str
    evidence_title: str
    title_override: str | None = None
    matched_observations: list[Observation] = field(default_factory=list)
    matched_services: list[Service] = field(default_factory=list)
    matched_technologies: list[Technology] = field(default_factory=list)
    matched_operating_systems: list[OperatingSystem] = field(default_factory=list)
