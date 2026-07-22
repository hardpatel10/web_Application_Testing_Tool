"""Every registered pipeline rule, grouped one module per topic.

``web_rules`` is listed before ``reserved_rules`` deliberately: the registry
(``backend.pipeline.registry.PipelineRuleRegistry``) evaluates rules in this
order and stops at the first non-``None`` verdict for a given service, so a
port that could plausibly match more than one category (there are none
today, but this keeps the ordering intentional rather than incidental)
resolves to the more specific web verdict first.
"""

from backend.pipeline.base import PipelineRule
from backend.pipeline.rules import reserved_rules, web_rules

ALL_RULES: tuple[type[PipelineRule], ...] = web_rules.RULES + reserved_rules.RULES
