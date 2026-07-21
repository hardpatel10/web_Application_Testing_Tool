"""``CorrelationRuleRegistry``: the static, in-memory catalog of every registered rule.

Deliberately simple compared to :mod:`backend.plugins.registry` -- rules are
not dynamically discovered from disk, so there is no loader, no health
check, no enable/disable state. Just a fixed, importable list plus id
lookup, instantiated once per rule class (rules are stateless).
"""

from backend.correlation.base import CorrelationRule
from backend.correlation.rules import ALL_RULES
from backend.models.enums import RuleCategory


class CorrelationRuleRegistry:
    """Read-only catalog over every registered :class:`CorrelationRule`."""

    def __init__(self) -> None:
        instances = [rule_class() for rule_class in ALL_RULES]
        ids = [rule.rule_id for rule in instances]
        duplicates = {rule_id for rule_id in ids if ids.count(rule_id) > 1}
        if duplicates:
            raise ValueError(f"Duplicate correlation rule id(s): {sorted(duplicates)}")
        self._rules: list[CorrelationRule] = instances
        self._by_id: dict[str, CorrelationRule] = {rule.rule_id: rule for rule in instances}

    def all_rules(self) -> list[CorrelationRule]:
        return list(self._rules)

    def get(self, rule_id: str) -> CorrelationRule | None:
        return self._by_id.get(rule_id)

    def by_category(self, category: RuleCategory) -> list[CorrelationRule]:
        return [rule for rule in self._rules if rule.category == category]

    def __len__(self) -> int:
        return len(self._rules)


_registry: CorrelationRuleRegistry | None = None


def get_rule_registry() -> CorrelationRuleRegistry:
    """Return the process-wide rule registry, constructing it on first access."""
    global _registry
    if _registry is None:
        _registry = CorrelationRuleRegistry()
    return _registry
