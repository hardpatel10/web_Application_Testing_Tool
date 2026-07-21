# Project Memory

## Project Name

Security Assessment Dashboard

---

## Purpose

A localhost platform for orchestrating open-source security assessment tools.

---

## Scope

The application executes tools.

It is NOT itself a scanner.

---

## Current Status

Phase 8 complete (Asset Inventory & Observation Engine).

Backend: FastAPI + async SQLAlchemy 2.0 (26 models) + Alembic (7 migrations), full assessment/target CRUD, the plugin framework, Tool Management, the real Assessment Execution Engine (Phase 6), Nmap as the reference scanner plugin with Scan Profiles (Phase 7), and now a durable, deduplicated Asset Inventory (Phase 8) — `Asset`/`NetworkInterface`/`Service`/`Technology`/`OperatingSystem`/`Observation`/`ObservationEvidence`/`Fingerprint`/`ExecutionAsset`/`ExecutionObservation`, merged (not duplicated) across repeated scans of the same host via deterministic fingerprinting, with full execution history. 5 new read-only API resources (`/assets`, `/services`, `/technologies`, `/observations`, `/operating-systems`) plus `/search`. 125 passing tests, verified live against real Nmap scans including a real re-scan proving the merge engine.

Plugin framework has 15 detection-only tool plugins (Nuclei, WhatWeb, Nikto, HTTPX, Gobuster, Dirsearch, Feroxbuster, FFUF, SSLScan, Katana, Naabu, Subfinder, Amass, DNSx, plus `example-plugin`) whose `execute()` still refuses, and Nmap as the one real, executing reference plugin (real subprocess, real XML parsing, real normalization into the Asset Inventory — never a Finding/CVSS/vulnerability).

Frontend: Assessments, Tools, Executions pages, plus new Assets/Services/Technologies/Observations/Operating Systems/Search pages (Phase 8) — all read-only inventory views with search/filter/sort/pagination, an Asset Details page with 7 tabs (Overview/Network Interfaces/Services/Technologies/Operating System/Observations-with-inline-evidence/Execution History). Reports/Settings still Phase-1 stubs. No ⌘K command palette (Search is a real page, not a modal).

Findings/correlation/reports not started — `Finding`/`FindingEvidence`/`FindingReference` remain scaffolded since Phase 2 but completely untouched, reserved for a future Correlation phase.

No auth (by design — single-user localhost app, confirmed again in Phase 3 instructions).

---

## Long-Term Goals

- Plugin architecture
- Assessment management
- Findings correlation
- Reporting
- PDF generation
- Dashboard
- Tool management
- Task execution
- Execution history

---

## Plugin Interface

Every plugin implements:

check_installation()

version()

validate_target()

build_command()

execute()

parse()

normalize()

health()

---

## Design Philosophy

Simple

Modular

Production-ready

Secure

Extensible

---

## Never Do

❌ Fake scan data

❌ Dummy vulnerabilities

❌ Hardcoded outputs

❌ Tool-specific logic in the core

❌ Business logic inside UI

❌ Massive files

---

## Always Do

✔ Small modules

✔ Strong typing

✔ Async operations

✔ Structured logging

✔ Dependency injection

✔ Input validation

✔ Error handling

✔ Unit-testable code

---

## Current Phase

Phase 8 complete: Asset Inventory & Observation Engine.

Waiting for approval before Phase 9. Explicitly not started per Phase 8's own instruction: Nuclei integration, correlation engine, any Finding/severity/CVSS.

See `security-assessment-dashboard/TASKS.md` and `security-assessment-dashboard/DECISIONS.md` for full detail.