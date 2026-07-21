# Security Assessment Dashboard

A workflow orchestration platform for open-source security tools. The platform does not implement vulnerability detection itself — it executes installed tools, collects their output, normalizes results, correlates findings, and generates reports.

> **Status:** Phase 4 — Plugin Framework & Plugin SDK complete. Assessment/target management and the plugin architecture (discovery, validation, loading, registry) are implemented. Authentication (by design), real tool integrations, tool execution, scanning, reports, findings, and background workers are intentionally not yet implemented — see `TASKS.md` and `DECISIONS.md` for full phase-by-phase detail.

## Project Overview

Security teams typically run several independent open-source tools (static analyzers, dependency scanners, network scanners, etc.) and manually stitch together their output. This project provides a single orchestration layer that:

- Detects which supported tools are installed on the host
- Executes them against a target and captures raw output
- Normalizes tool-specific output into a common internal format
- Correlates findings across tools
- Produces consolidated reports

The application never fabricates results. If no scan has been run, the UI says so explicitly rather than showing placeholder data.

## Architecture

The backend follows a layered, dependency-injected architecture:

```
Routes (HTTP I/O only)
   -> Services (business logic, framework-agnostic)
      -> Plugins / Database (execution, persistence)
```

- **Routes** parse requests, delegate to a service, and serialize the response. No logic lives here.
- **Services** contain the actual application logic and depend only on abstractions (settings, session factories), never on FastAPI internals.
- **Plugins** (introduced in a later phase) are isolated adapters around individual security tools. A plugin's only responsibilities are: detect installation, execute the tool, capture output, parse output, and normalize output. Plugins never touch the database, render UI, generate reports, or correlate findings — that is the orchestration layer's job.
- **Schemas** (Pydantic v2) define the contract at every boundary (HTTP request/response).
- Configuration, logging, exception handling, and security utilities are centralized under `core/` so the rest of the codebase depends on a single abstraction rather than scattered environment reads.

The frontend is a standard feature-oriented React SPA: `layouts/` for shell chrome (sidebar, topbar, breadcrumbs), `pages/` for route-level views, `components/ui/` for shadcn/ui primitives, `store/` for global client state (Zustand), and `services/` for the API client.

## Folder Structure

```
security-assessment-dashboard/
├── backend/
│   ├── api/
│   │   ├── routes/          # Versioned HTTP endpoints (thin controllers)
│   │   ├── dependencies/    # FastAPI dependency providers (DI wiring)
│   │   └── middleware/      # ASGI middleware (request logging, etc.)
│   ├── core/                # Config, structured logging, exceptions, security utils
│   ├── database/            # Async engine/session, declarative base, Alembic migrations
│   ├── models/               # SQLAlchemy ORM models (Phase 2+)
│   ├── schemas/              # Pydantic request/response models
│   ├── services/             # Business logic, independent of the HTTP layer
│   ├── plugins/              # Security tool plugin adapters (Phase 2+)
│   ├── reporting/            # Report generation (Phase 2+)
│   ├── workers/              # Background task workers (Phase 2+)
│   ├── utils/                 # Small, stateless helpers
│   ├── tests/                 # Pytest suite
│   ├── main.py                 # FastAPI app factory + ASGI instance
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── assets/           # Static assets bundled by Vite
│   │   ├── components/       # Shared UI components (ui/ = shadcn/ui primitives)
│   │   ├── features/         # Feature-scoped modules (Phase 2+)
│   │   ├── hooks/            # Shared React hooks (Phase 2+)
│   │   ├── layouts/          # Shell chrome: sidebar, topbar, breadcrumbs
│   │   ├── pages/             # Route-level views
│   │   ├── routes/            # Router configuration and navigation data
│   │   ├── services/           # API client
│   │   ├── store/               # Zustand global state (theme, etc.)
│   │   ├── styles/               # Global CSS + design tokens
│   │   ├── types/                 # Shared TypeScript types
│   │   ├── utils/                  # Shared utilities (cn, etc.)
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── public/
│
├── docs/           # Architecture documentation
├── docker/         # Development Dockerfiles
├── reports/        # Generated report output (gitignored)
├── scripts/        # Local developer convenience scripts (PowerShell)
├── plugins/        # External/user-installed plugin artifacts (Phase 2+)
├── .env.example
├── docker-compose.yml
└── README.md
```

## Tech Stack

**Backend:** Python 3.13, FastAPI, Uvicorn, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, AsyncIO, SQLite (PostgreSQL-compatible).

Chosen for a fully async, type-checked backend with a mature migration story: FastAPI + Pydantic v2 gives validated request/response contracts for free; SQLAlchemy 2.0's async engine keeps the whole stack non-blocking; Alembic is driven by the same `Settings.database_url` used at runtime so the SQLite-to-PostgreSQL swap requires no code changes, only a connection string.

**Frontend:** React, TypeScript, Vite, React Router, TanStack Query, Zustand, TailwindCSS, shadcn/ui, Recharts, React Hook Form, Zod.

Chosen for a fast dev loop (Vite), strict typing end-to-end, and a clean split between server state (TanStack Query — not yet wired to real data in Phase 1) and lightweight client state (Zustand, currently used for the theme). shadcn/ui components are copied into the repo (not an npm dependency) so they can be freely customized; Tailwind provides the design tokens driving both light and dark themes.

**Database:** SQLite initially, with the engine, session factory, and Alembic environment all built against a single `DATABASE_URL` so the migration to PostgreSQL is a configuration change, not a rewrite.

## Installation

Prerequisites: Python 3.13+, Node.js 20+, npm.

```powershell
git clone <repository-url>
cd security-assessment-dashboard
Copy-Item .env.example .env
```

`.env` is optional for local development — every setting has a working default (see `backend/core/config.py`); the run scripts below create it for you automatically if it's missing.

### Backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

### Database migrations

```powershell
.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
```

Must be run from the project root (not `backend\`) — `alembic.ini` and `Settings` both resolve paths relative to the current working directory. Safe to re-run; it's a no-op once the database is already at the latest revision.

### Frontend

```powershell
cd frontend
npm install
```

## Running Locally

The easiest way to start everything is the run scripts at the project root, which install dependencies, create `.env` if missing, apply migrations, and start each server with clear status output — see **Quick Start** below.

### Quick start (recommended)

```powershell
# Backend only
.\backend\run_backend.ps1        # or backend\run_backend.bat

# Frontend only
.\frontend\run_frontend.ps1      # or frontend\run_frontend.bat

# Both, each in its own window
.\run_all.ps1                    # or run_all.bat
```

### Backend (manual)

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API is served under `/api/v1`. Interactive docs: `http://localhost:8000/docs` (Swagger) and `http://localhost:8000/redoc` (ReDoc) — both reflect the exact set of endpoints implemented so far (assessments, targets, plugins, health/version/system), so they're the authoritative reference rather than a list duplicated here.

### Frontend (manual)

```powershell
cd frontend
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api` requests to `http://localhost:8000` (see `frontend/vite.config.ts`) — start the backend first.

### Startup order

1. Backend (must be up before the frontend can load real data; the frontend itself will still start without it, but every page will show request errors).
2. Frontend.

### Docker (development)

```powershell
docker compose up --build
```

### Tests

```powershell
.venv\Scripts\python.exe -m pytest backend\tests -v
```

## Future Roadmap

- **Phase 2:** Database models and Alembic migrations for assessments, tools, findings, and reports.
- **Phase 3:** Plugin system — tool detection, execution, and output normalization.
- **Phase 4:** Scan orchestration and background workers.
- **Phase 5:** Finding correlation across tools.
- **Phase 6:** Report generation (PDF/HTML export).
- **Phase 7:** Authentication and authorization.
- **Phase 8:** Full dashboard UI wired to real assessment data (charts, findings tables, tool status).

## License

MIT — see [LICENSE](LICENSE).
