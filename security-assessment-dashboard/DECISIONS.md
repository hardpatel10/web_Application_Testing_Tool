# Architecture Decisions

Records non-obvious technical decisions and the reasoning behind them.
Phase 1's stack/layering decisions are covered in `docs/ARCHITECTURE.md`;
this file starts with Phase 2.

## Phase 2 — Core Database & Domain Model

### UUID primary keys via SQLAlchemy's cross-dialect `Uuid` type

Used `sqlalchemy.Uuid(as_uuid=True)` rather than a `String(36)` column.
Maps to a native `UUID` column on PostgreSQL and a `CHAR(32)` hex column on
SQLite from the same model definition — no SQLite-specific type leaks into
the ORM layer, keeping the stated PostgreSQL-compatibility goal true
without extra code.

### Enums stored as `VARCHAR`, not native DB enums

Every enum column uses `Enum(..., native_enum=False, validate_strings=True)`.
SQLite has no native enum type; Postgres does, but native enums are
painful to alter later (`ALTER TYPE ... ADD VALUE` has restrictions).
Storing as a `CHECK`-constrained `VARCHAR` costs nothing at our scale and
is portable and easy to extend in a future migration.

> **Correction (Phase 3):** this entry's premise was wrong in practice —
> `Enum(..., native_enum=False)` alone does *not* add a `CHECK` constraint
> under SQLAlchemy 2.0 (its `create_constraint` default changed to `False`).
> Every enum column was an unconstrained `VARCHAR` until Phase 3 added
> `create_constraint=True` everywhere and retrofitted the missing
> constraints via migration. See the Phase 3 entry below.

### Explicit constraint-naming convention on `Base.metadata`

SQLAlchemy leaves auto-generated constraint/index names implementation-defined
unless a naming convention is set. Without one, Alembic's SQLite "batch"
migration mode (needed for any future `ALTER TABLE`, since SQLite can't
alter columns/constraints directly) can't reliably target a constraint by
name. Set once now in `backend/database/base.py`; free for every future
migration.

### SQLite foreign-key enforcement via a connect-event listener

SQLite ignores `FOREIGN KEY` constraints — including `ON DELETE
CASCADE`/`RESTRICT` — unless `PRAGMA foreign_keys=ON` is issued on every
new connection; it is not a database-wide setting. Without this, the
cascade/restrict rules declared on the models would parse and migrate
fine but silently do nothing at runtime. Added as a `connect` event
listener in `backend/database/session.py`, applied only when the dialect
is SQLite (a no-op, correctly-behaving PostgreSQL doesn't need it).

### `ToolExecution.tool_id` is `ON DELETE RESTRICT`; everything else under an `Assessment` is `CASCADE`

An assessment fully owns its targets, executions, findings, notes,
reports, and attachments — deleting the assessment should delete all of
it. A `Tool`, however, is a shared catalog row (the plugin subsystem's
concept of "nmap" or "nikto") that historical executions reference for
audit purposes; deleting a tool while executions still reference it would
silently destroy execution history. `RESTRICT` makes that impossible at
the database level rather than relying on service-layer discipline.

### `ToolConfiguration` is one-to-one with `Tool` (unique `tool_id`), not one-to-many

This is a single-user, single-machine application (see `CLAUDE.md`'s
no-auth/no-multi-user constraint) — there is no concept of per-user or
per-environment tool configs, so a single set of defaults per tool is
sufficient and avoids an unused "which config is active" concept.

### `AssessmentTool` is a composite-primary-key entity, not a plain association `Table`

It carries its own attributes (`enabled`, `execution_order`), so it needs
to be addressable and updatable as a first-class row, not just an
implicit many-to-many link. Modeled as an ORM class with primary key
`(assessment_id, tool_id)` rather than a bare `sqlalchemy.Table`.

### `RawToolOutput` and `Finding.cvss_score` get `CHECK` constraints, not just application validation

`raw_tool_outputs` requires `file_path IS NOT NULL OR raw_text IS NOT NULL`
— a row with neither would silently represent "no output," which is a
data-integrity bug, not a valid state. `findings.cvss_score` is
constrained to `[0, 10]`, the valid CVSS range. Both are cheap,
permanent guarantees at the database level that no future service-layer
bug can violate.

### Generic `Repository` never commits

`backend/database/repository.py` flushes (to surface DB errors and
populate defaults/PKs immediately) but never commits. The transaction
boundary belongs to whoever composes repository calls into a unit of
work — typically a service method or the request-scoped session
dependency — so a service can call multiple repository methods across
different models and have them succeed or fail atomically together.

## Phase 3 — Assessment Management & Target Management

### `Enum(create_constraint=True)` added everywhere; missing `CHECK` constraints retrofitted

Discovered while writing this phase's migration: SQLAlchemy 2.0 changed
`create_constraint`'s default to `False` for non-native enums, so every
enum column in the schema — going back to Phase 2 — was actually an
unconstrained `VARCHAR`. Verified with a raw-SQL insert of a garbage
status value that should have been rejected and wasn't. Every model's
`Enum(...)` now passes `create_constraint=True` explicitly, and the
Phase 3 migration adds the missing `CHECK` retroactively to every
existing enum column, not only the three whose value sets changed.

### `deleted_at` (soft delete) is orthogonal to `status == ARCHIVED`

The prompt is explicit: deleting an assessment must never delete its
on-disk files, and archiving/restoring is its own reversible workflow
state. Conflating the two (e.g. treating delete as "set status to some
deleted-ish value") would make "restore a deleted assessment" and
"archive with memory of the prior status" fight over the same field.
`status` (enum, includes `ARCHIVED`) and `deleted_at` (nullable
timestamp) are independent: an assessment can be archived-and-not-deleted,
deleted-and-not-archived, or (in principle) both.

### `Assessment.previous_status` exists solely to make `restore` correct

Not in the prompt's literal field list, but required to implement
"Restore Archived Assessment" *correctly* rather than resetting every
restored assessment to an arbitrary default. Set on archive, read and
cleared on restore. A small, justified addition — not a speculative one.

### Duplicating a target refuses to fabricate IPv4/IPv6/CIDR values

`targets` has a per-assessment unique constraint on `target_value`, so an
exact clone can never be inserted. For hostname/domain/URL, appending a
`copy-`/`-copy` marker keeps the value meaningfully related to the
original and guaranteed unique. For IP-shaped types there is no safe
"nearby" address to invent without fabricating data that could be
mistaken for something the user actually intended to scan — CLAUDE.md's
"never generate placeholder data" extends to this case even though it's
about targets, not scan results. The API requires an explicit
`target_value` for IPv4/IPv6/CIDR duplication instead.

### Target validation lives in one stdlib-only module, used by both the service and the standalone `/validate` endpoint

`backend/utils/target_validators.py` has no I/O and no DB access — pure
functions built entirely on `ipaddress`, `urllib.parse`, and `re`. Both
`TargetService` (create/update/bulk-import) and the dry-run `/validate`
route call the exact same functions, so there is exactly one definition
of "what makes a valid IPv4/IPv6/CIDR/hostname/domain/URL" in the
codebase, per CLAUDE.md's "no duplicated logic."

### Configurable default paths live in `Settings` (env-configurable), not the `ApplicationSetting` DB table

Phase 2 built `ApplicationSetting` as a key/value store partly with this
use case in mind, but Phase 3's API surface doesn't call for a settings
CRUD UI or endpoints — nothing would ever write to those DB rows yet.
Adding a DB-backed settings-resolution layer with no consumer is
speculative. `assessment_root_dir`/`reports_dir`/`exports_dir`/
`temp_dir`/`backups_dir` are `Settings` fields instead, following the
exact pattern already established by `log_dir` — env-var configurable
today, trivially promotable to `ApplicationSetting`-backed once a
settings UI actually exists to edit them.

### `get_db_session` commits once per request, rolls back on exception

Phase 2 deferred this ("the transaction boundary belongs to the
caller... typically the request-scoped session dependency"). Phase 3 is
the first phase with mutations, so it's implemented now: a service can
call several repository/session operations and have them commit or roll
back together as one unit of work, with no service method needing to
manage its own transaction boundary.

### Frontend forms use plain `useState`, not `react-hook-form`/`zod` (both already installed)

Client-side validation would duplicate the exact rules already enforced
by `target_validators.py` and the Pydantic schemas — a second, divergent
copy of "what's a valid target" that could drift from the backend's.
Forms submit and surface the backend's validation errors via toast
instead. Simpler, and there is exactly one source of truth for validity.

## Phase 4 — Plugin Framework & Plugin SDK

### Plugin manifests reuse `backend.models.enums.TargetType`/`RawOutputFormat` rather than plugin-only duplicates

`backend/plugins/models/enums.py` only defines the two concepts genuinely
new to the plugin framework (`SupportedPlatform`, `PluginHealthStatus`).
For `supported_targets`/`supported_output_formats`, the obvious-sounding
"decouple the plugin SDK from the app's domain enums" instinct was
rejected: `TargetType`/`RawOutputFormat` in `backend.models.enums` are
plain `StrEnum`s with zero SQLAlchemy/DB import — importing them isn't a
plugin-touches-persistence violation, it's sharing a vocabulary module.
Defining a second, value-identical enum for the sole purpose of an
architectural boundary that doesn't actually exist yet would be exactly
the kind of speculative duplication `CLAUDE.md`'s "no duplicated logic"
warns against. If the two ever need to diverge, split them then.

### `PluginMetadata` is always derived from `PluginManifest`, never populated by hand

`PluginMetadata.from_manifest()` is the only way a `PluginMetadata` gets
built. A plugin's `metadata()` method calls it against `self._manifest`
rather than constructing the object field-by-field, so a plugin's
declared capabilities can never drift from its own `plugin.json`.

### Plugin exceptions are a separate hierarchy from `backend.core.exceptions`, translated at the service boundary

`backend/plugins/exceptions/` has its own `PluginError` base with no
FastAPI/HTTP awareness — the plugin framework doesn't depend on the web
layer at all. `backend/services/plugin_service.py` catches
`PluginNotFoundError` and re-raises `backend.core.exceptions.NotFoundError`,
mirroring exactly how `TargetService` translates a missing DB row into an
HTTP-aware exception. Keeps `backend/plugins/` importable and testable
with no FastAPI installed, in principle.

### Plugin directories are loaded as synthetic packages via `importlib.util`, not as real submodules of `backend.plugins.plugins`

The first implementation imported each plugin as
`backend.plugins.plugins.<name>.<module>` and relied on `backend.plugins.plugins`
being an implicit PEP 420 namespace package. That only works when
`plugins_root` is literally the on-disk `backend/plugins/plugins/`
directory — Python's import system resolves that dotted name via
`backend.plugins`'s own `__path__`, not via any runtime-configured
`Settings.plugins_dir`. Since `plugins_dir` is an env-configurable
`Settings` field specifically so an operator *could* point it elsewhere,
the loader instead builds an ad-hoc `ModuleSpec(is_package=True,
submodule_search_locations=[plugin_directory])` per plugin, registers it
under a fresh uuid-suffixed name in `sys.modules`, then loads the
entrypoint module against that spec. This makes a plugin's relative
imports (`from .parser import ...`) work no matter where its directory
actually lives, and was caught by a test that deliberately discovered a
plugin from a `tmp_path` outside the repo — the first implementation
failed that test with `ModuleNotFoundError`, which is exactly the bug
this design avoids. The loader tracks the last synthetic package name
used per directory so a reload purges the old one instead of leaking a
fresh module set into `sys.modules` on every `POST /plugins/reload`.

### `PluginRegistry`/`PluginManager`/`PluginLoader` are constructor-injected, not `Settings`-aware

Only the DI wiring in `backend/api/dependencies/plugins.py` reads
`Settings.plugins_dir`; the plugin framework's own classes take a plain
`Path`/collaborator objects. Keeps `backend/plugins/` framework-agnostic
about configuration and directly unit-testable against an arbitrary
`tmp_path`, per `CLAUDE.md`'s "Dependency Injection friendly" quality bar.

### `PluginConfiguration` (enabled/timeout/working dir/args/env/temp dir) is in-memory only, not DB-persisted

No settings table or UI to edit it exists yet (same reasoning as Phase
3's "configurable paths live in `Settings`, not `ApplicationSetting`"
decision) — building persistence with no consumer would be speculative.
Defaults reset on process restart; promoting this to a DB-backed model
is a small, isolated change whenever a settings UI actually needs it.

### `defusedxml` added as a new backend dependency for the SDK's XML helper

Plugins parse XML *produced by security tools scanning untrusted
targets* — a hostile server's response can end up reflected into a
scanner's XML report. Python's own documentation flags `xml.etree`'s
standard parser as unsafe against maliciously crafted input (XXE,
entity-expansion). This is the one new dependency added this phase,
justified directly by `CLAUDE.md`'s "Security" principle rather than
convenience.

### `PluginRegistry.check_dependencies` resolves `manifest.dependencies` against other *registered plugin ids*, not `required_binaries`

The manifest has two distinct dependency-like fields.
`required_binaries` is an installation/environment concern a plugin
checks about itself via `check_installation()`/`health()` (e.g.
`shutil.which`). `dependencies` (a list of other plugin ids) is an
inter-plugin graph-integrity concern that only the registry — which
knows the full set of currently loaded plugins — can actually answer, so
that's where "dependency checking" (a requirement named at the registry
level) lives.

## Phase 5 — Tool Management & Tool Configuration

### Bug found in the Phase 4 loader: a plugin instance and its registry wrapper had two different default configs

`PluginLoader._load_one` called `plugin_class(manifest)` (no config —
`BasePlugin.__init__` defaulted `self._config` to a fresh
`PluginConfiguration()`) and separately built `RegisteredPlugin(...)`
whose own `config` field defaulted to *another* fresh
`PluginConfiguration()`. The two objects were never the same instance, so
mutating `registered.config` (e.g. from a future configuration API) would
never have been visible to the running plugin's own `self._config` — it
would have looked like configuration silently did nothing. Phase 5 is the
first phase where configuration actually needs to affect plugin behavior
(`build_command()`, `resolve_executable()`), which is what surfaced this.
Fixed by constructing one `PluginConfiguration` and passing the *same
object* to both the plugin instance and its `RegisteredPlugin` — mutating
either one now mutates both, since they're the same reference.

### `ToolService` reuses Phase 2's `Tool`/`ToolConfiguration` tables rather than inventing new ones

Phase 2 already scaffolded exactly this: a `tools` catalog table and a
one-to-one `tool_configurations` table, with a docstring saying
"populated and kept in sync by the plugin subsystem (a later phase)".
Phase 5 is that later phase. Extending the existing schema (new
`status`/`health_status`/`health_message`/`last_checked_at` columns on
`Tool`; a fuller configuration surface on `ToolConfiguration`) instead of
adding parallel tables keeps `AssessmentTool`/`ToolExecution`'s existing
foreign keys meaningful and avoids a second, competing "what is a tool"
concept.

### `Tool.name` *is* the plugin manifest id — no separate `plugin_id` column

The phase brief asks to display both "Name" and "Plugin ID" per tool.
`Tool.name` was already a unique, indexed technical identifier (Phase 2);
making it equal to the plugin's manifest id (e.g. `"nmap"`) satisfies
both display requirements with one column, and lets `GET /tools/{name}`
use a short, human-readable path parameter instead of a UUID lookup —
consistent with how Phase 4's `/plugins/{id}` already worked.

### `ToolHealthStatus` (healthy/warning/error) is a new, coarser enum — not a reuse of `PluginHealthStatus`

Phase 4's `PluginHealthStatus` has 5 values
(healthy/degraded/unhealthy/not_installed/unknown) and lives in the
plugin framework, framework-agnostic about any particular application.
The phase brief explicitly asks for exactly 3 health states
(Healthy/Warning/Error) for Tool Management's UI. Rather than force the
framework's enum to match one UI's vocabulary (or force this UI to show
5 values nobody asked for), `ToolHealthStatus` is a new enum in
`backend.models.enums`, and `ToolService` maps one to the other at the
boundary. Contrast with the Phase 4 decision to *reuse*
`TargetType`/`RawOutputFormat`: the difference is that those were
identical concepts with identical values, while this is a deliberately
different, coarser vocabulary — reuse only when it's genuinely the same
concept, not by default.

### `ToolStatus` derivation: not-enabled beats everything; version-unparseable is "Unsupported Version," not "Degraded"

`ToolService._derive_status` order: `enabled=False` → `DISABLED` (the
user's own choice always wins); not found on disk → `MISSING`; found but
a configured custom executable path or wordlist path fails validation →
`MISCONFIGURED`; found but no version string could be parsed at all →
`UNSUPPORTED_VERSION`; otherwise `INSTALLED`. The brief names
"Unsupported Version" as a status without defining per-tool minimum
versions to check against — inventing a minimum-version policy with no
stated requirement would be speculative. Interpreting it instead as "we
found the binary but can't even read a version out of it" is the one
version-related failure this phase can actually evaluate honestly.

### Tool configuration is validated and persisted, then pushed onto the *same* live `PluginConfiguration` object

`ToolService.update_configuration` writes the DB row and then mutates
`registered.config`'s fields in place (not `registered.config = new_obj`)
— because it's the same object the running plugin instance already reads
via `self._config` (see the loader bug fix above), an in-place mutation
takes effect immediately, with no plugin reload required. Replacing the
object instead would have silently detached the registry's bookkeeping
copy from the instance's live copy again.

### The wordlist/path "Browse" dialog is backed by a new `GET /tools/browse-filesystem` endpoint, not a native `<input type="file">`

Browsers deliberately never expose a selected file's absolute path (a
security boundary against a website fingerprinting the local
filesystem), so a client-side file input cannot produce something like
`/home/user/wordlists/common.txt` for the backend to actually use. Since
this is a single-user, localhost-only, no-auth-by-design application (the
browser and the backend already run on the same machine, on the same
trust boundary — see `.claude/CLAUDE.md`), a small read-only,
directory-listing endpoint is a reasonable, explicitly scoped answer: it
only ever returns names/paths/is-directory, never file contents.

### `defusedxml`/JSON-lines parsing is real per-tool, but `execute()` always refuses

Every plugin's `parser.py`/`normalizer.py` contains genuine, tool-accurate
parsing logic (XML via `defusedxml` for Nmap/Nikto/SSLScan; JSON-lines for
the Go-based scanners) even though nothing calls `execute()` to produce
real output to parse yet. This is deliberately different from fabricating
data: it's real, reviewable code for a known, documented output format,
written once now so a future execution phase doesn't have to write it
under time pressure — while `execute()` itself (the one method that would
actually run a tool) is shared in `DetectionOnlyPlugin` and unconditionally
raises, so there is no path — accidental or otherwise — to running a real
scan this phase.

## Phase 6 — Assessment Execution Engine

### Bug: a job cancelled before its own `try/except` had run even one line was left stuck forever

`ExecutionManager._execute_job`'s original `try` block only wrapped the
code *after* the job had already been loaded and flipped to `PREPARING` —
so a cancellation landing before that point propagated straight through,
uncaught, into `_run_job`'s blanket `except asyncio.CancelledError: pass`,
leaving the job's DB row at `queued`/`preparing` forever with nothing to
ever finalize it. Widening that `try` to wrap the entire method (locals
seeded to `None` beforehand, guarded at each use site) closed most of the
window, but a second, more fundamental gap remained underneath it: a
directly-verified Python asyncio behavior (see the reproduction below) is
that cancelling a `Task` *before its coroutine has executed a single
line* never actually enters that coroutine's frame at all — a `try/except`
wrapping the entire function body simply does not fire, because there is
no frame to unwind. No code written inside `_run_job`/`_execute_job` can
ever observe that specific timing. The fix has to live somewhere that
fires unconditionally regardless of whether the coroutine ever ran: a
task's `add_done_callback`, which always fires once a task is done, cancelled-before-first-step
included. `ExecutionManager._on_worker_done` (already the done-callback
that releases the semaphore) now also spawns a small
`_ensure_cancelled_finalized(job_id)` safety-net task — a no-op if the job
already reached a terminal status (the normal case, if `_execute_job`'s own
handling caught it), and the only place left that finalizes a job as
`CANCELLED` when it didn't.

Reproduction that proved the underlying semantics (not this app's code —
plain `asyncio`):
```python
async def job():
    try:
        await asyncio.sleep(0.05)
    except asyncio.CancelledError:
        caught.append("caught inside job")  # never appended
        raise

async def main():
    task = asyncio.create_task(job())
    task.cancel()          # cancelled before job() has run a single line
    try:
        await task
    except asyncio.CancelledError:
        caught.append("caught at await task")  # this is what actually fires
```

### `ExecutionManager.shutdown()` waits for safety-net tasks instead of cancelling them, in a loop

The safety-net task above is spawned from a *done callback*, so a fixed
snapshot-then-cancel-then-gather `shutdown()` (the natural first attempt)
can miss one: cancelling a task in `_running_tasks` can itself trigger
`_on_worker_done`, which creates a *new* safety-net task after `shutdown()`
already built its list to await. That orphaned task would then outlive
the event loop it was created on — surfaced directly as
`RuntimeError: Event loop is closed` from an orphaned `aiosqlite`
background thread, since the backend test suite gives every test function
its own event loop. `shutdown()` now cancels only the genuinely
long-running tasks (`_running_tasks`, the dispatcher), then *awaits*
(never cancels) whatever is left in `_finalize_safety_net_tasks`, looping
with a `sleep(0)` checkpoint since one more can still appear as the ones
just awaited finish. These are quick DB writes, not long-running work, so
waiting for them is both correct and cheap; cancelling one mid-write would
just reproduce the exact "stuck in a non-terminal status" bug one level
down.

### SQLite gets a 30s busy-timeout and WAL journal mode, added in this phase

Every phase through Phase 5 only ever had one DB writer at a time (one
HTTP request, handled sequentially) — this phase is the first to give the
single SQLite file genuine concurrent writers (job worker tasks, the
cancellation safety-net task, and the HTTP request session, all
potentially mid-transaction at once) on top of the frontend's 1.5s
polling adding frequent concurrent readers. Under SQLite's default
rollback-journal mode, readers and writers block each other; stress-testing
this phase's cancellation path surfaced `sqlite3.OperationalError: database
is locked` directly, and — worse, after just raising the busy-timeout —
minutes-long stalls rather than a clean failure, indicating real
contention rather than one occasional collision. WAL mode (readers proceed
concurrently with a single writer, the standard fix for SQLite under
concurrent asyncio access) plus a 30s busy-timeout (`connect_args={"timeout":
30}`, for the writer-vs-writer contention WAL doesn't eliminate) together
resolved it across 50+ stress-test repetitions. Both are `backend/database/session.py`
changes, gated to the `sqlite` dialect only — a future PostgreSQL target
needs neither.

### Test suite disposes the DB engine between tests

A related discovery, not a production bug: `backend/database/session.py`'s
`_engine` is a module-level singleton reused by every test, while each
test function gets its own fresh event loop
(`asyncio_default_fixture_loop_scope = function`). A connection checked
back into the pool at the end of one test can be handed to the *next*
test's session on a different loop — but `aiosqlite`'s background worker
thread for that connection still holds a reference to the loop it was
opened on, so a later callback lands on an already-closed loop. This can
never happen in the real running application (one process, one event loop,
for its entire lifetime) — it is purely an artifact of per-test event
loops sharing one engine. `tests/conftest.py`'s `client` fixture now calls
`await _engine.dispose()` after each test, forcing a fresh connection on
whichever loop uses the engine next, per SQLAlchemy's own guidance for
async engines exercised across multiple event loops in a test suite.

### A job reaching a terminal status and its assessment reverting status are two separate commits — tests must poll for both

`ExecutionManager._finalize()` commits the job's row, publishes an event,
*then* `_on_job_terminal()`/`_finalize_assessment()` commits the
assessment's row — a few `await`s apart, with no atomicity across them
visible to an external caller. Two tests
(`test_cancel_running_job_and_assessment_reverts_status`,
`test_execute_plans_and_completes_jobs`) originally read the assessment's
status exactly once, immediately after polling the *job* to a terminal
status — a real, if narrow, race: under load, that single read can land in
the gap before the assessment's own commit. Both now poll for the
assessment status via a new `_wait_for_assessment_status` helper, mirroring
the job-status polling helper that already existed. The production
sequencing itself is correct and unchanged; only the tests' assumption of
single-read consistency was wrong.

### `dummy-execution`'s default sleep duration can only be changed by editing its source, not via a live API

Verifying cancellation/retry against the real running dev server (not just
pytest) needed a job that stayed `running` long enough to cancel.
`PUT /tools/{name}/configuration` looked like the obvious lever, but it is
`ToolService`-owned and assumes every registered plugin is a
`DetectionOnlyPlugin` (calls `resolve_executable()`, which
`DummyExecutionPlugin` — a plain `BasePlugin`, never one of the 15 real
tools — does not have); calling it against `dummy-execution` throws
`AttributeError`, a real 500. This is not a bug to fix: `dummy-execution`
is deliberately excluded from `ToolService.SUPPORTED_TOOL_IDS` and was
never meant to be reachable through Tool Management's configuration path
(its own module docstring says exactly this). The live demonstration
instead used a small, reversible edit to the plugin's own
`_DEFAULT_DURATION_SECONDS` constant (0.2s → 4.0s, reverted immediately
after), rather than extending `ToolService` to support arbitrary
non-detection plugins it was never scoped to handle.

## Phase 7 — Nmap Integration with Scan Profile Engine

### A synthetically-loaded plugin's exception classes have a different identity than the same dotted import path used outside the plugin

The Phase 4 loader builds each plugin's package via a synthetic
`importlib.util.ModuleSpec` so relative imports work regardless of where
the plugins root actually lives on disk (see that phase's own section
below). A side effect: `backend.plugins.plugins.nmap.profile_manager.ProfileValidationError`
imported through the normal dotted path from outside the plugin gets a
*different class object* than the one the plugin's own, synthetically-loaded
module actually raises at runtime — `except ProfileValidationError` at the
service boundary silently never matches, surfacing as an unhandled 500.
Caught live while testing the built-in-profile edit/delete guards. Fixed by
having the plugin's own exceptions (`ProfileNotFoundError`/
`ProfileValidationError`) inherit from the plugin *framework's* stable,
singly-loaded base exceptions (`backend.plugins.exceptions`) and catching
those instead — and by changing `ProfileManager.create_custom`/`update_custom`
to accept plain `dict`s rather than pre-built `ScanProfile` instances, so no
external caller ever needs to construct one of a synthetically-loaded
plugin's own Pydantic types at all. General lesson, applicable to any future
plugin: never catch a plugin's own exception subclasses from outside the
plugin package via the normal dotted path; catch the framework's stable base
exception instead, and pass plain dicts/primitives across that boundary, not
plugin-owned model instances.

## Phase 8 — Asset Inventory & Observation Engine

### Asset identity is scoped per-assessment, not globally

Confirmed with the user before implementation (three architectural
judgment calls asked up front, since getting the schema wrong here would
mean redoing the migration): the same IP in two different assessments is
treated as two different assets, mirroring `Target`'s existing
`uq_targets_assessment_id_target_value` pattern. Private IPs are
legitimately reused across networks/clients — a single global `Asset` row
keyed only on IP would incorrectly merge unrelated hosts from different
engagements that happen to share a private address.

### `Fingerprint` (the entity) and `fingerprint` (the merge-key column) are deliberately two different things

The phase brief uses "fingerprint" for two different concepts: a table of
captured protocol-level identity *evidence* (SSH host keys, TLS certs, SMB
signing, banners — things a plugin observed) and a deterministic dedup key
used to decide "have I seen this host/service/observation before." These
were kept as separate mechanisms rather than conflated into one: the new
`Fingerprint` model stores the former (evidence, optional, informational);
`Asset.fingerprint`/`Service.fingerprint`/`Observation.fingerprint` computed
columns (via `backend.services.fingerprinting`, pure sha256-based functions)
drive the latter (the actual merge-lookup unique index). Single
responsibility: one identifies, the other records.

### Observation has no severity/confidence, despite the phase brief listing them as fields

Asked and confirmed with the user: the phase's own philosophy ("Observation
is NOT a vulnerability") directly conflicts with the brief's literal field
list and its "Observation View" spec (which shows Severity/Confidence as
columns). Resolved in favor of the philosophy — Observation stays strictly
factual, with zero risk-adjacent fields. `Finding.severity`/`.confidence`
(Phase 2, still completely untouched) remain the only place a risk judgment
can ever be recorded, reserved for a future Correlation phase.

### The write-side merge engine and the read-side query service are two separate classes

`AssetInventoryService` (`backend/services/asset_inventory_service.py`) is
the only place a `NormalizedOutput` becomes persisted rows — called
exclusively from `ExecutionManager` after a completed job. `AssetInventoryQueryService`
(`backend/services/asset_inventory_query_service.py`) backs the five new
read-only API resources. Kept as two classes rather than one, even though
they operate on the same tables: the write side's correctness depends on
transactional find-or-insert-or-update ordering within one job's
persistence; the read side is stateless search/filter/sort/pagination with
no write concerns at all. Merging them would make an already-nontrivial
merge algorithm harder to reason about for no benefit.

### `Enum(create_constraint=True)`'s CHECK constraint survives an explicit `drop_constraint()` in Alembic's SQLite batch mode

Discovered while verifying `downgrade()` on the Phase 8 migration — the one
migration in this project so far with real production data on the line (6
assets/47 services/2 observations from prior sessions' live testing, not a
disposable test DB). Dropping a column whose type is
`sa.Enum(..., create_constraint=True)` via `batch_op.drop_column(...)`
correctly excludes the column from the recreated table's DDL, but the
CHECK constraint tied to it (created under its own bare `name=`, not the
table's `ck_<table>_<name>` naming-convention form) keeps getting
re-emitted by batch mode's table-recreate regardless of an explicit
`batch_op.drop_constraint('<bare_name>', type_='check')` beforehand —
verified directly: the constraint drop succeeds without error, and the
next statement still fails with `no such column: category` referencing the
just-dropped column inside the recreated `CREATE TABLE`. This reproduced
identically for both `observations.category` and `assets.asset_type`. Not
pursued further past two fix attempts — matches this project's own
established precedent (every prior migration's documented SQLite
batch-mode `downgrade()` limitation, Phases 3/5/7) that `upgrade()` is the
one path that must be fully verified against real data; `downgrade()`'s
fix here was to simply leave those two enum columns undropped (harmless,
nullable, unused post-downgrade) rather than keep fighting an Alembic/
SQLite interaction with diminishing returns for a rarely-exercised path.

### Re-verifying `GET /jobs/{id}/results` live caught a real regression this phase's own schema change caused

`ExecutionService.get_results` (`backend/services/execution_service.py`,
built in Phase 7, consumed by the Phase 7 frontend's `JobResultsView`)
queried `Asset.execution_id` directly and read `asset.ip_address`/`.os_name`/
`.os_accuracy` — all four removed by this phase's `Asset` restructuring.
Nothing in the Phase 8 test suite exercises this specific endpoint (it
belongs to the Phase 6/7 execution engine, not the new inventory
resources), so it would have shipped broken — caught only because this
session's own practice is to re-verify existing live endpoints after a
schema change that touches their tables, not just the newly-added ones.
Fixed by joining through the new `ExecutionAsset` table instead of the
removed direct FK, and deriving the job-results view's OS name/accuracy
from the asset's single best-accuracy `OperatingSystem` candidate across
its *entire* history — arguably more correct than before, since OS
detection may have run on an earlier scan and that knowledge is still
current, not a per-job snapshot. General lesson: a schema-restructuring
phase must re-verify every *existing* consumer of the changed tables, not
only the new code being added — grep for the changed field/column names
across the whole backend before considering the phase done.

### The `ExecutionAsset.is_new` flag must reflect whether `_upsert_asset` inserted a row, not whether the fingerprint was already seen earlier in the same batch

A real bug caught during implementation, before it ever ran: an early draft
computed `is_new` from a local `touched_assets_this_run` set (used to avoid
inserting a duplicate `ExecutionAsset` row when one job's normalized output
mentions the same host twice) — but by the time that flag was read, the
fingerprint had *already* been added to the set a line earlier, so `is_new`
would always evaluate `False`. `_upsert_asset` now explicitly returns
whether it inserted a new `Asset` row or found an existing one, and that
boolean — not set membership — is what `ExecutionAsset.is_new` records. The
`touched_assets_this_run` set still exists, but only for its original
purpose (never violating the `(execution_id, asset_id)` unique constraint
within one job), decoupled from discovery-vs-reconfirmation semantics.

## Phase 9 — Correlation Engine & Intelligence Dashboard

### The Correlation Engine is triggered explicitly (`POST /correlation/run`), never wired into `backend.workers.manager.ExecutionManager`

The phase brief is explicit: "Do NOT modify the execution engine." Phase 8's
`AssetInventoryService.persist()` is already called directly from
`ExecutionManager._persist_scan_results` — the closest existing precedent for
"a completed job triggers a service" — but that wiring was built *during*
Phase 8, the phase that owned the execution engine at the time. Phase 9 does
not own it; `backend/workers/*.py` is frozen, tested code with a real
documented concurrency-bug history (see Phase 6's entries above), and the
brief's own framing — "Create a **dedicated** Correlation Engine" — reads as
a deliberately separate pipeline stage, not a hook appended to the existing
one. Correlation instead runs on its own explicit trigger: a new
`POST /correlation/run` endpoint (not in the brief's literal GET-only API
list, but a necessary, minimal addition — without some trigger the engine
could never run at all) that the frontend calls from a visible "Run
Correlation" button on the Dashboard/Findings pages. `CorrelationRun` (a new
table) gives `GET /correlation/status` a real history to report instead of
guessing "did anything run."

### `Finding` is deduplicated exactly like `Asset`/`Service`/`Observation` — one fingerprint per `(rule_id, asset)`, not one row per rule evaluation

Phase 8 established the pattern (`fingerprint` column + unique index,
`first_seen`/`last_seen`, re-running the source process finds-and-updates
rather than inserting) for exactly this kind of "the same real-world fact
gets reported repeatedly across scans" problem. A `Finding` is that same
kind of fact — "this rule's condition is true for this asset" — so it gets
the same treatment: `finding_fingerprint(rule_id, asset.fingerprint)`,
verified idempotent by running the Correlation Engine twice against the same
data (0 created / 40 re-confirmed on the second pass, real dev data). A rule
that returns *multiple* `FindingCandidate`s for one asset in one run (e.g.
`SVC-005` matching both an exposed Redis and an exposed Elasticsearch on the
same host) does not produce multiple `Finding` rows — every candidate is
merged onto the same one finding as additional evidence. This is the
brief's own "Merging" requirement taken literally: "If multiple observations
indicate the same issue, create ONE finding, maintain all evidence."

### No rule ever attaches a CVE or a CVSS score

The brief simultaneously asks for a `Finding.cvss_score` field (inherited
from Phase 2) *and* says "Do NOT fabricate CVEs" / "References must be real.
Do not invent IDs." A specific CVSS score requires expert judgment about a
specific vulnerability instance; assigning one from a rule with no NVD/CVE
lookup available would be exactly the kind of fabrication CLAUDE.md
forbids. Every rule's `references` tuple only ever cites a real, verifiable
CWE or OWASP Top 10 category (e.g. `CWE-319` cleartext transmission,
`CWE-306` missing authentication, `A05:2021` security misconfiguration) —
general, well-established weakness classifications, never a specific CVE
number tied to a specific software version. `cvss_score` stays `NULL` for
every correlation-engine-generated finding; the column remains for a
possible future analyst-entry workflow, not populated automatically.

### Confidence escalation falls back to `ExecutionAsset` reconfirmation count when a rule has no supporting observations

The brief: "Increase confidence when multiple observations support the same
finding." Rules keyed purely on `Service`/`Technology`/`OperatingSystem` data
(e.g. `SVC-003` SMB exposed, `OS-001` EOL OS) have no `Observation` rows to
count at all — `Service`/`Technology` don't carry a `plugin`/execution-history
concept of their own the way `Observation` does. Rather than leaving these
rules permanently stuck at base confidence regardless of how many times a
scan re-confirms them, `CorrelationService._compute_confidence` counts
distinct confirming executions via `ExecutionAsset` (the asset's own
re-scan history, already durable since Phase 8) whenever a finding has zero
linked observations. Verified directly: an asset scanned across 9 separate
executions (this project's own real dev data) produces `SVC-003`/`SVC-005`
findings at `CONFIRMED` confidence, not stuck at the rule's `HIGH`/`MEDIUM`
base value.

### `Finding.plugin` is resolved via a real join, not hardcoded `"nmap"`

Every rule in this phase happens to only ever see Nmap-sourced data today,
which made a `plugin = "nmap"` constant tempting. Rejected: a future
Nuclei/other-scanner phase would then need to remember to come back and fix
every rule, and until then the field would be lying by omission about its
own provenance. `CorrelationService._resolve_asset_plugin` instead joins
`Asset.source_execution_id -> ToolExecution.tool_id -> Tool.name` once per
asset — genuinely correct today and requires zero changes when a second
scanner starts populating the same tables.

### Two real bugs, both caught only by real-browser (Playwright) verification, not by `tsc`/`eslint`/pytest

1. `DistributionBarChart`'s `<Cell key={row.label}>` produced duplicate
   React keys whenever two categories legitimately shared a display label —
   "Findings by Asset" showing ten different `localhost` assets (Asset
   identity is scoped *per-assessment* since Phase 8, so the same hostname
   legitimately recurs across separate assessments scanning the same
   machine) all collided under the identical key. Fixed in two places: the
   `Cell` key now includes the array index (a pure rendering-correctness
   fix), and `DashboardService._disambiguate()` appends a short id suffix
   (`localhost (055a25d7)`) to any label that collides with another in the
   same result set (a real UX-honesty fix — the underlying ambiguity was
   real, not just a React warning).
2. `TrendAreaChart`'s `margin={{ left: -20 }}` (added to visually tighten
   the chart against its card padding) clipped the Y-axis tick labels down
   to unreadable fragments that read, at a glance, like a repeated "0" —
   confirmed by a zoomed-in screenshot showing labels present but sliced.
   Neither the type checker nor the linter can catch a layout value that is
   *valid* CSS/props but visually wrong; only looking at the rendered output
   caught it. Fixed by removing the negative margin and widening the axis
   gutter instead. General lesson (consistent with this project's established
   "no browser automation tool other than a disposable Playwright script is
   available in this environment" practice): a chart that type-checks and
   builds cleanly can still render illegibly, and step 7 of the dataviz
   skill's own procedure — "render it and look at it" — is not optional.

### The migration is a plain drop-and-recreate of `findings`/`finding_evidence`/`finding_references`, not a staged additive/backfill/tighten migration

Unlike every table Phase 8 touched, `findings` (scaffolded in Phase 2) had
never been written to by any phase through Phase 8 — confirmed directly
(`SELECT COUNT(*) FROM findings` = 0) against the real dev database
immediately before writing this migration, and its two child tables can only
be non-empty if it is. With zero rows genuinely on the line, Phase 8's
three-pass "nullable columns -> Python backfill -> tighten" dance (necessary
there because real scan data existed) would be pure ceremony here. The
migration drops and recreates all three tables in one step, guarded by a
runtime `_assert_findings_table_is_empty()` check that aborts `upgrade()`
(rather than silently discarding data) if that assumption is ever wrong on
some other environment.
