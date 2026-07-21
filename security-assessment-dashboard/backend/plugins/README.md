# Plugin Framework

This package is the architecture that lets any future security tool be
added to the Security Assessment Dashboard **without modifying the
application core**. It does not integrate any tool itself — see
`backend/plugins/plugins/example_plugin/` for the one internal reference
plugin, which exists only to prove the framework works and never executes
anything real.

Per `.claude/CLAUDE.md`'s plugin philosophy, a plugin only:

- detects installation
- executes the tool
- captures its output
- parses that output
- normalizes it into the platform's common shape

A plugin never modifies the database, renders UI, generates reports, or
correlates findings. Nothing in this package does any of those things
either — that enforcement is structural: `BasePlugin`'s constructor takes
only a manifest and a configuration object, so a conforming subclass has
no path into the DB session, HTTP layer, or report generator through its
base class.

## Directory structure

```
backend/plugins/
├── core/            BasePlugin — the abstract contract every plugin implements
├── sdk/              Reusable helpers plugin authors import (validators, JSON/XML/
│                       file/temp helpers, logging, curated re-exports of core/models)
├── models/          Pure data models: manifest, metadata, health, config, execution
│                       context/output, validation result. No I/O, no DB, no FastAPI.
├── exceptions/      PluginLoadError / PluginValidationError / PluginExecutionError /
│                       PluginConfigurationError / PluginDependencyError / PluginNotFoundError
├── validators/      Framework-level validation: manifest schema, directory structure,
│                       interface compliance (distinct from sdk validators, which validate
│                       *targets* for plugin authors)
├── registry/        In-memory store of loaded plugins: dedup by id, enable/disable,
│                       lookup, dependency checking
├── loader/          Filesystem discovery + dynamic import of plugin directories
├── manager/         High-level facade (list/get/reload/validate/health/installed) used
│                       by the API layer; owns the process-wide singleton
└── plugins/         Installed plugin directories live here (see Layout below)
```

## Plugin lifecycle

1. **Discovery** (`loader.PluginLoader.discover`) — scans every immediate
   subdirectory of the plugins root (`Settings.plugins_dir`, default
   `backend/plugins/plugins/`).
2. **Structure validation** — the required files are all present (see
   Layout below).
3. **Manifest validation** — `plugin.json` parses as JSON and satisfies
   the `PluginManifest` schema.
4. **Import** — the manifest's `entrypoint` module is dynamically loaded
   as a synthetic package rooted at the plugin's own directory (so its
   `plugin.py` can use ordinary relative imports to reach
   `parser.py`/`normalizer.py`/`validator.py`), independent of where
   `plugins_dir` actually points on disk.
5. **Interface validation** — the entrypoint class subclasses
   `BasePlugin` and implements every abstract method.
6. **Instantiation** — the class is constructed with its manifest and a
   default `PluginConfiguration`.
7. **Registration** — added to the `PluginRegistry`, which rejects a
   duplicate id.

Any failure at steps 2-6 is recorded as a `DiscoveredPlugin(success=False,
error=...)` with a specific message; discovery continues with the next
plugin directory rather than aborting. A plugin never crashes the
application by being broken.

Re-running discovery (`PluginManager.reload_all()` /
`POST /api/v1/plugins/reload`) clears the registry and repeats the whole
process, so edits to a plugin's files on disk take effect without
restarting the app ("hot discovery").

## Required layout

```
plugins/
    plugin_name/
        plugin.json     # manifest — see below
        plugin.py       # defines the BasePlugin subclass named in entrypoint
        parser.py       # parses this tool's raw output
        normalizer.py   # normalizes parsed output to the common shape
        validator.py    # validates/narrows target support for this tool
        README.md       # what this plugin is, its status, any caveats
```

All six files are required; `backend.plugins.validators.structure_validator`
rejects a directory missing any of them before its manifest is even read.

## Manifest (`plugin.json`)

```json
{
  "id": "example-plugin",
  "name": "Example Plugin",
  "version": "0.1.0",
  "entrypoint": "plugin:ExamplePlugin",
  "author": "Security Assessment Dashboard",
  "description": "...",
  "license": "MIT",
  "homepage": null,
  "documentation_url": null,
  "supported_platforms": ["linux", "macos", "windows"],
  "supported_targets": ["hostname", "ipv4"],
  "supported_output_formats": ["json"],
  "required_binaries": [],
  "dependencies": []
}
```

| Field | Notes |
|---|---|
| `id` | Lowercase, `[a-z][a-z0-9_-]*`. Must be unique across all loaded plugins. |
| `name` | Human display name. |
| `version` | Semantic version, e.g. `1.0.0` or `1.0.0-beta.1`. |
| `entrypoint` | `'<module_stem>:<ClassName>'`, e.g. `'plugin:ExamplePlugin'` — resolved relative to this directory. |
| `author`, `description`, `license` | Free text. |
| `homepage`, `documentation_url` | Optional URLs (plain strings, or `null`). |
| `supported_platforms` | Any of `linux`, `macos`, `windows`. |
| `supported_targets` | Reuses `backend.models.enums.TargetType` (`ipv4`, `ipv6`, `cidr`, `hostname`, `domain`, `url`) — see *Design note* below. |
| `supported_output_formats` | Reuses `backend.models.enums.RawOutputFormat` (`xml`, `json`, `txt`, `html`, `csv`). |
| `required_binaries` | Executable names this plugin's `check_installation()` looks for (e.g. via `shutil.which`). |
| `dependencies` | Other plugin `id`s this plugin expects to also be registered. Checked by `PluginRegistry.check_dependencies`. |

**Design note:** `supported_targets`/`supported_output_formats` intentionally
reuse the domain enums already defined in `backend.models.enums` rather than
defining plugin-only duplicates — those enums are plain, DB-agnostic
`StrEnum`s with zero SQLAlchemy coupling, so importing them here isn't a
layering violation, and it avoids two independent definitions of "what's a
valid target type" drifting apart over time.

## `BasePlugin` — the required interface

Every plugin's entrypoint class extends `backend.plugins.sdk.BasePlugin`
(or `backend.plugins.core.BasePlugin` — the SDK just re-exports it) and
implements:

| Method | Responsibility |
|---|---|
| `metadata()` | Return this plugin's `PluginMetadata` (build via `PluginMetadata.from_manifest(self.manifest)`). |
| `health()` | Return a `PluginHealth` — installed/degraded/unhealthy status. |
| `check_installation()` | Whether required binaries are present (no execution). |
| `get_version()` | Detected installed tool version, if determinable. |
| `validate_target(target_type, target_value)` | Whether this plugin can run against a target. |
| `prepare(context)` | Any setup needed before building a command. |
| `build_command(context)` | The argv this plugin would execute. |
| `execute(command, context)` | Run the command, return a `PluginRawOutput`. |
| `parse(raw_output)` | Parse raw output into an intermediate structure. |
| `normalize(parsed_output)` | Normalize into the platform's common shape. |
| `cleanup(context)` | Release any resources created during execution. |

Nothing in this phase calls `execute()` for real — there is no task queue
or orchestrator yet (deliberately out of scope; see `TASKS.md`). The
interface exists in full now so a future execution engine can be built
against a stable contract without changing every existing plugin.

## Validation

`backend.plugins.validators.PluginValidator` runs three independent
passes, aggregated into a `PluginValidationResult` (`valid`, `errors`,
`warnings`):

1. **Structure** — all six required files present.
2. **Manifest** — `plugin.json` is valid JSON and satisfies the
   `PluginManifest` Pydantic schema (id format, semver, entrypoint format,
   valid enum values, etc.).
3. **Interface** — the entrypoint class subclasses `BasePlugin` and has no
   remaining `__abstractmethods__`.

The loader runs all three before ever registering a plugin (fail closed).
`GET /api/v1/plugins/{id}/validate` re-runs the same three passes
on-demand for an already-registered plugin (report-only).

## SDK (`backend.plugins.sdk`)

The curated surface plugin authors should import against:

- `BasePlugin` and every model (`PluginManifest`, `PluginMetadata`,
  `PluginHealth`, `PluginConfiguration`, `PluginExecutionContext`,
  `PluginRawOutput`) and exception type.
- `is_valid_target` / `normalize_target` / `detect_target_type` — delegate
  to `backend.utils.target_validators`, the one place target validation
  rules live.
- `safe_json_loads` / `safe_json_dumps` — JSON helpers that return `None`
  instead of raising.
- `safe_xml_parse` — XML parsing via `defusedxml`, not the standard
  library's `xml.etree` directly, since plugins parse tool output that may
  reflect content from an untrusted scanned target (XXE hardening).
- `ensure_directory` / `read_text_file` / `write_text_file` — file helpers.
- `plugin_temp_directory` — a context manager wrapping
  `tempfile.TemporaryDirectory`.
- `get_plugin_logger(plugin_id)` — returns a logger under the
  `plugins.<id>` namespace.

## Writing a new plugin

1. Create `backend/plugins/plugins/<your_tool>/`.
2. Add the six required files (see Layout above).
3. Write `plugin.json` with a unique `id` and accurate `supported_*`
   fields.
4. In `plugin.py`, define a class extending `BasePlugin` and implement
   every method — delegate to `parser.py`/`normalizer.py`/`validator.py`
   for the actual logic, keeping `plugin.py` as thin orchestration (see
   `example_plugin/plugin.py`).
5. `check_installation()`/`get_version()` should shell out to nothing more
   than a version check of the tool itself (e.g. `tool --version`) — no
   scan execution.
6. Restart the app, or `POST /api/v1/plugins/reload`, and confirm it
   appears in `GET /api/v1/plugins` with `validation_valid: true`.

## Explicitly out of scope this phase

No task queue, no process execution, no findings, no reports, no
correlation. `execute()`/`build_command()` are part of the interface but
nothing invokes them against a real tool yet — that's a future phase's
orchestrator, built against this same `BasePlugin` contract.
