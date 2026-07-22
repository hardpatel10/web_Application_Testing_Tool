"""``PipelineRuleRegistry``: the static, in-memory catalog of every registered pipeline rule.

Mirrors :class:`backend.correlation.registry.CorrelationRuleRegistry` --
a fixed, importable list plus id lookup, instantiated once per rule class
(rules are stateless). Unlike the correlation registry, rule order is
meaningful here: :meth:`decide` returns the first non-``None`` verdict,
since exactly one rule should ever claim a given service.
"""

from backend.models.discovered_host import DiscoveredHost
from backend.models.service import Service
from backend.pipeline.base import PipelineRule
from backend.pipeline.models import PipelineDecision
from backend.pipeline.rules import ALL_RULES


class PipelineRuleRegistry:
    """Read-only catalog over every registered :class:`PipelineRule`, in evaluation order."""

    def __init__(self) -> None:
        instances = [rule_class() for rule_class in ALL_RULES]
        ids = [rule.rule_id for rule in instances]
        duplicates = {rule_id for rule_id in ids if ids.count(rule_id) > 1}
        if duplicates:
            raise ValueError(f"Duplicate pipeline rule id(s): {sorted(duplicates)}")
        self._rules: list[PipelineRule] = instances

    def all_rules(self) -> list[PipelineRule]:
        return list(self._rules)

    def decide(self, service: Service, host: DiscoveredHost) -> PipelineDecision:
        """The first rule's non-``None`` verdict on ``service``, or ``None`` if nobody claims it."""
        for rule in self._rules:
            decision = rule.evaluate(service, host)
            if decision is not None:
                return decision
        return None

    def __len__(self) -> int:
        return len(self._rules)


_registry: PipelineRuleRegistry | None = None


def get_pipeline_rule_registry() -> PipelineRuleRegistry:
    """Return the process-wide pipeline rule registry, constructing it on first access."""
    global _registry
    if _registry is None:
        _registry = PipelineRuleRegistry()
    return _registry
