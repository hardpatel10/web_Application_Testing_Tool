"""The Correlation Engine: turns normalized inventory facts into ``Finding`` rows.

Deliberately its own top-level package, parallel to ``backend.plugins`` and
``backend.workers`` — per this phase's brief ("Create a dedicated
Correlation Engine") and its explicit "do not modify the execution engine"
constraint, this package only ever *reads* ``DiscoveredHost``/``Service``/
``Technology``/``OperatingSystem``/``Observation`` rows that Phase 6-8's
frozen execution engine already persisted; it never touches
``backend.workers`` or the Nmap plugin.

- ``models``: the pure, DB-agnostic ``RuleContext``/``FindingCandidate``/``RuleReference`` shapes a rule evaluates against and returns.
- ``base``: the ``CorrelationRule`` interface every rule implements.
- ``registry``: the static, in-memory list of every registered rule.
- ``rules``: the real rule implementations, one module per ``RuleCategory``.

Rules are plain, code-reviewed Python classes -- not a dynamically loaded
plugin system like ``backend.plugins`` -- because a correlation rule is a
judgment call about what constitutes a real, evidence-backed security
finding, and CLAUDE.md's "never fabricate a finding" bar means every rule
in this package must be reviewable, deterministic source code, never
arbitrary third-party or user-supplied logic.
"""
