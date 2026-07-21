# Security Assessment Dashboard

You are acting as the lead software architect for this repository.

## Project Goal

Build a production-quality Security Assessment Dashboard that orchestrates open-source security tools.

The platform does NOT implement vulnerability detection itself.

It executes installed tools, collects outputs, normalizes results, correlates findings, and generates reports.

---

## Core Principles

Always prioritize:

- Clean Architecture
- SOLID principles
- Modular design
- Security
- Maintainability
- Readability
- Extensibility

Never sacrifice architecture for speed.

---

## Development Rules

Never generate placeholder data.

Never create fake scan results.

Never simulate vulnerabilities.

Never mock security tool output unless explicitly requested for testing.

Only display real collected data.

---

## Plugin Philosophy

Every tool is an isolated plugin.

Plugins only:

- detect installation
- execute tool
- capture output
- parse output
- normalize output

Plugins NEVER:

- modify database
- render UI
- generate reports
- correlate findings

---

## Backend Stack

FastAPI

SQLAlchemy

Alembic

Pydantic v2

AsyncIO

SQLite initially

PostgreSQL compatible

---

## Frontend Stack

React

TypeScript

Vite

TanStack Query

React Router

Zustand

TailwindCSS

shadcn/ui

Recharts

---

## Code Quality

Use:

- type hints
- docstrings
- logging
- dependency injection
- configuration classes
- structured exceptions

Avoid:

- global variables
- duplicated logic
- hardcoded paths
- tightly coupled modules

---

## Every Phase

After completing work:

1. Show created files
2. Explain architecture
3. Explain design decisions
4. Wait for approval

Never continue automatically.