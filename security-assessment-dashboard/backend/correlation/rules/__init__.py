"""Every registered correlation rule, grouped one module per ``RuleCategory``."""

from backend.correlation.base import CorrelationRule
from backend.correlation.rules import (
    configuration_rules,
    cross_tool_rules,
    general_rules,
    http_rules,
    os_rules,
    protocol_rules,
    service_rules,
    smb_rules,
    ssh_rules,
    technology_rules,
    tls_rules,
)

ALL_RULES: tuple[type[CorrelationRule], ...] = (
    service_rules.RULES
    + technology_rules.RULES
    + os_rules.RULES
    + protocol_rules.RULES
    + configuration_rules.RULES
    + tls_rules.RULES
    + ssh_rules.RULES
    + smb_rules.RULES
    + http_rules.RULES
    + general_rules.RULES
    + cross_tool_rules.RULES
)
