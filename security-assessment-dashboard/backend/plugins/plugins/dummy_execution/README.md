# Dummy Execution Plugin

Internal, non-tool-integrating plugin used **only** to exercise the
Assessment Execution Engine (`backend/workers/`) end-to-end: planning,
queuing, concurrency limiting, progress reporting, cancellation, retry,
and live logging.

It never starts an external program and never produces a real finding —
`execute()` only `asyncio.sleep`s, then returns a fixed, fabricated
result. It is discovered by the plugin framework exactly like any other
plugin (proving discovery does not special-case it), but is never listed
in `backend.services.tool_service.SUPPORTED_TOOL_IDS` and never shown in
Tool Management, exactly like `example-plugin` (Phase 4's plugin
framework reference fixture).

## Behavior control

Since there is no real command-line tool to reflect, behavior is driven
entirely by `PluginExecutionContext.extra_arguments`:

- `"duration:<seconds>"` — how long `execute()` sleeps before finishing (default `0.2`)
- `"fail"` — finish with a non-zero exit code and stderr instead of success
- `"raise"` — raise an exception instead of returning (simulates a crash)

Tests set these via the registered plugin's live `PluginConfiguration.arguments`
(the same list the execution engine reads for every plugin), not through
any Tool Management UI/API — this plugin has no `Tool` catalog row unless
a test creates one itself.
