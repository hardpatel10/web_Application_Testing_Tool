"""The Assessment Execution Engine.

Coordinates running installed tool plugins against an assessment's
targets: planning jobs (:mod:`backend.workers.planner`), queuing them
(:mod:`backend.workers.queue`), dispatching a bounded pool of concurrent
asyncio workers that call into each plugin's ``prepare()``/
``build_command()``/``execute()`` (:mod:`backend.workers.manager`), and
publishing lifecycle events (:mod:`backend.workers.events`) that drive
structured per-job logging (:mod:`backend.workers.logger`) and the
assessment activity log.

Contains zero tool-specific logic -- it only ever calls the generic
``BasePlugin`` interface. See ``backend/plugins/README.md`` for the
plugin contract this engine drives, and this phase's entry in
``DECISIONS.md`` for why this package (not a new top-level one) is where
that "later phase" the ``backend.workers`` docstring used to promise
turned out to live.
"""
