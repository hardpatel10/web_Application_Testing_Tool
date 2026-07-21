"""``CorrelationRule``: the interface every rule in :mod:`backend.correlation.rules` implements.

Mirrors :class:`backend.plugins.core.base_plugin.BasePlugin`'s shape
(class-level metadata + one behavioral method) deliberately -- this
codebase already has one well-tested convention for "a self-describing unit
with fixed metadata plus one evaluation method," so the rule engine reuses
it instead of inventing a second one.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from backend.correlation.models import FindingCandidate, RuleContext, RuleReference
from backend.models.enums import FindingConfidence, FindingSeverity, RuleCategory


class CorrelationRule(ABC):
    """One deterministic, evidence-backed correlation rule.

    Every rule declares the fixed metadata the phase brief requires ("Rule
    ID, Title, Description, Category, Severity, Conditions, Evidence
    Requirements, References, Remediation") as class attributes -- a
    ``Finding`` never carries a rule-specific field that didn't originate
    from exactly one of these, so a rule's metadata and a finding's
    persisted shape can never drift apart.
    """

    rule_id: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]
    category: ClassVar[RuleCategory]
    severity: ClassVar[FindingSeverity]
    base_confidence: ClassVar[FindingConfidence] = FindingConfidence.MEDIUM
    impact: ClassVar[str]
    remediation: ClassVar[str]
    references: ClassVar[tuple[RuleReference, ...]] = ()

    @abstractmethod
    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        """Return zero or more matches for this one host's current, real, collected data.

        Must be a pure function of ``context`` -- no I/O, no randomness, no
        clock reads -- so the same inventory state always produces the same
        finding (or no finding at all). Returning ``[]`` is the overwhelmingly
        common case; a rule only returns a candidate when its own documented
        condition is actually, deterministically satisfied by real data.
        """
        raise NotImplementedError
