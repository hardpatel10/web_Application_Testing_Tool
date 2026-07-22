"""The Assessment Pipeline: decides which follow-up scanners make sense from what Nmap discovered.

Mirrors :mod:`backend.correlation`'s shape and philosophy deliberately --
a fixed catalog of pure, deterministic rules (:mod:`backend.pipeline.rules`)
evaluated by a registry (:mod:`backend.pipeline.registry`), with all
DB/execution-engine orchestration confined to :mod:`backend.pipeline.engine`.
Rules only ever *decide*; they never touch the database or the execution
engine themselves.
"""
