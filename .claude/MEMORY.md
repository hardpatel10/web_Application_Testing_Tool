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

## Runtime Platform

**Runtime: Linux ONLY.** The application is only ever deployed and run on Linux.

**Development: Windows (development only, via Claude Code).** Code is written on Windows; after every phase it is copied to a Linux machine to run and test. Windows is never a supported runtime target, and no dual-platform (Windows + Linux) logic is maintained in application code — only Windows-only developer convenience launcher scripts (`.ps1`/`.bat`) are kept, alongside real Linux equivalents (`.sh`) that are the scripts that actually matter for the runtime.

Tool discovery uses Linux-only conventions (`PATH`/`which` + common Linux install directories); tools are invoked by their bare Linux binary name (`nmap`, not `nmap.exe`). See `docs/LINUX_TOOL_INSTALLATION.md` for per-tool Linux install instructions.

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

diagnostics() — added Phase 10; one shared implementation on `DetectionOnlyPlugin` covering every tool plugin (resolved path, detection method, version command/raw output, health), not reimplemented per tool.

Three tool plugins now have real execution + a Scan Profile system (`models.py`/`command_builder.py`/`profile_manager.py`/`profiles/*.json` each): Nmap (Phase 7), Nikto and Nuclei (Phase 11). The other 13 remain detection-only. The HTTP-facing `ScanProfileRead`/`ScanProfileWrite` schema is a superset of all three tools' own profile fields (Nmap's ports/scripts, Nikto's tuning/plugins, Nuclei's templates/tags/severities), each optional — see DECISIONS.md's Phase 11 section for why this generalization was a real bug fix, not a pre-existing design.

---

## Navigation & Information Architecture

Main navigation is exactly seven items: Dashboard, Assessments, Tools, Executions, Findings, Reports, Settings (`frontend/src/routes/nav-items.ts`). Internal data-model concepts (hosts/services/technologies/observations/operating systems) are **never** standalone nav destinations or top-level routes — that data is real and fully queryable via the backend (nothing was removed there), it's just surfaced contextually: inside an Assessment's own tabs (Overview/Targets/Executions/Findings/Assets Discovered/Raw Results/Reports/History), inside a Finding's Affected Host/Affected Services, or inline within a selected host's drill-down. Before adding any new standalone page to the nav, ask whether the data is genuinely a top-level concept (an assessment-workflow noun) or an internal inventory concept that belongs nested instead.

`/security-overview` is a real, still-existing route (severity distribution + critical-findings summary) that is deliberately **not** in the nav array — reachable via a button on the Findings page instead. Don't remove it as "orphaned" without checking Findings.tsx first.

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

Phases 1-9 complete, an out-of-band architectural change (Linux-only runtime, Windows development-only), Phase 10 (Tool Management 2.0), and now **Phase 11 (Nikto & Nuclei Integration) complete**: both upgraded from detection-only stubs to real, executing plugins with their own Scan Profile systems (9 built-in profiles each, matching the phase brief's exact lists), following Nmap's reference architecture exactly. New cross-tool Correlation rules (`backend/correlation/rules/cross_tool_rules.py`) combine Nmap+Nikto+Nuclei observations into one Finding — verified end-to-end against a real database using the phase brief's own worked example (Apache 2.4.49 -> CVE-2021-41773). The `ExecuteDialog` was generalized from a hardcoded-to-Nmap profile picker into a real "3 steps, professional defaults first, Advanced Mode collapsed by default" experience for any profile-supporting tool.

Two real, generalizable bugs were found and fixed: (1) the shared Scan Profile HTTP schema was still hardcoded to Nmap's own field names, producing a real 500 the moment Nikto/Nuclei's differently-shaped profiles flowed through it — fixed by making it a proper superset schema; (2) `FindingCandidate.title_override` had been dead code since Phase 9 (declared, never read by the persistence layer) until this phase's cross-tool rules were the first to actually need it.

Real execution against Nikto/Nuclei was **not** demonstrated this session — neither tool is installed on this Windows dev machine, and installing them here would cut against the Linux-only-runtime workflow. Parsing/normalization was verified against realistic sample output instead; a skipif-guarded real-execution test exists for each and will run for the first time on the Linux machine.

**Then, a UI/UX refactor (same day, separate request): removed internal data model pages from the main navigation.** Deleted 8 standalone pages/routes (`/hosts`, `/hosts/:id`, `/host-overview`, `/services`, `/technologies`, `/technology-overview`, `/observations`, `/operating-systems`) — see the new "Navigation & Information Architecture" section above for the resulting nav shape. That data moved to contextual drill-down: 5 new tabs on Assessment Details (Executions/Findings/Assets Discovered/Raw Results/Reports), a `HostDetailPanel.tsx` extracted from the deleted `HostDetails.tsx` and rendered inline instead of at its own URL, Dashboard trimmed to remove all raw-inventory widgets (added Tool Status + Recent Activity instead, both explicitly requested), and Search/FindingDetails updated to deep-link into the owning Assessment instead of a deleted host page. **Zero backend functionality removed** — every model/table/route/normalization/correlation pipeline is untouched; one small additive field (`SearchResult.assessment_id`) was added since deep-linking search results into an Assessment was otherwise not implementable. Verified live end-to-end against a real Nmap scan + real correlation run, zero console errors.

Waiting for approval before Phase 12.

See `security-assessment-dashboard/TASKS.md` and `security-assessment-dashboard/DECISIONS.md` for full detail.