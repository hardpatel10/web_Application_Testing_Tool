# Security Assessment Dashboard

You are acting as the lead software architect for this repository.

## Project Goal

Build a production-quality Security Assessment Dashboard that orchestrates open-source security tools.

The platform does NOT implement vulnerability detection itself.

It executes installed tools, collects outputs, normalizes results, correlates findings, and generates reports.

---

## Runtime Platform

**Runtime Platform: Linux ONLY.** The application is only ever deployed and executed on Linux. Windows support is not a goal.

**Development Environment: Windows (development only).** Code is written on Windows using Claude Code, then copied to a Linux machine to run and test after every phase. Claude Code itself remains a Windows-hosted tool for editing this repository — that does not make Windows a supported runtime.

Rules that follow from this:

- Do not add Windows-specific code paths or dual-platform (`if platform.system() == "Windows"`) branching anywhere in application code. The only acceptable exception is a Windows-only *developer convenience* script (e.g. a `.ps1`/`.bat` launcher) that never ships and is never imported by the application itself.
- Assume every external security tool (`nmap`, `nuclei`, `nikto`, `whatweb`, `ffuf`, `katana`, `naabu`, `subfinder`, `amass`, `httpx`, `gobuster`, `dirsearch`, `feroxbuster`, `sslscan`, `dnsx`, ...) is invoked by its bare Linux binary name (`nmap`, never `nmap.exe`).
- Discover tools using Linux conventions only: `PATH` lookup (`shutil.which`) and common Linux install directories (`/usr/local/bin`, `/usr/bin`, `~/.local/bin`, `~/go/bin`, `/opt`, `/snap/bin`, ...). Never search Program Files, the Windows Registry, or AppData.
- Use `pathlib.Path` everywhere internally; never hardcode a backslash path or a drive letter.
- Use real Linux subprocess execution (`asyncio.create_subprocess_exec` with an explicit argv list). Never `shell=True`, never `cmd.exe`, never PowerShell.
- If a new Python dependency is needed for Linux functionality, update `backend/requirements.txt`.
- If a required external tool is missing on the host, detect it and surface it as "Not Installed" with Linux install instructions. Never auto-install it.
- Whenever a new external tool is integrated, document its Linux installation steps (apt/dnf/pacman and/or the official upstream method) in the project documentation.

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