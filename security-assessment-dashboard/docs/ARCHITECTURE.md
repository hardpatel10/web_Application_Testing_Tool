# Architecture Decisions

This document records decisions not fully covered by the README, and will grow as later phases add the plugin system, correlation engine, and reporting pipeline.

## Layering

```
HTTP request
  -> Middleware (CORS, request logging)
  -> Route (backend/api/routes/*) — parses request, calls a service, returns a schema
  -> Service (backend/services/*) — business logic, no FastAPI/Starlette imports
  -> Plugin / Database (later phases) — tool execution, persistence
```

Routes are kept intentionally thin. A route function should be readable as "validate input via the schema, call one service method, return." Anything more than that belongs in a service.

## Dependency Injection

FastAPI's `Depends()` is used throughout instead of module-level singletons, so every route's dependencies are explicit in its signature and swappable in tests. `Settings` is loaded once via `functools.lru_cache` and threaded through the dependency graph (`backend/api/dependencies/config.py`), rather than imported directly in service/route modules.

## Structured Logging

Three separate log streams are configured in `backend/core/logging.py`:

- `logs/app.log` — all application-level records
- `logs/api.log` — HTTP request/response records only (`RequestLoggingMiddleware`)
- `logs/error.log` — WARNING and above, across all loggers

Records are emitted as single-line JSON so they can be ingested by log aggregation tooling without a custom parser.

## Error Handling

All application-raised errors derive from `AppException` (`backend/core/exceptions.py`), which carries a stable `error_code` in addition to an HTTP status and message. Global handlers convert `AppException`, FastAPI's `RequestValidationError`, `HTTPException`, and any unhandled exception into the same JSON envelope:

```json
{ "error": { "code": "...", "message": "..." } }
```

This gives the frontend one shape to handle regardless of failure mode.

## Plugin Isolation (Phase 2+)

Plugins will be the only code allowed to invoke external tool binaries. A plugin's contract is limited to: detect installation, execute, capture output, parse, normalize. Plugins will not have database or reporting access — orchestration services own that responsibility. This keeps a compromised or buggy tool integration from being able to corrupt stored results or bypass correlation logic.

## PostgreSQL Compatibility

`DATABASE_URL` is the single source of truth for the database connection, consumed identically by the running application (`backend/database/session.py`) and by Alembic (`backend/database/migrations/env.py`). Moving from SQLite to PostgreSQL is a configuration change (swap the URL and driver) rather than a code change, as long as future models avoid SQLite-specific column types.
