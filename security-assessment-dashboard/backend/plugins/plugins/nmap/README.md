# Nmap Plugin

The reference implementation for a scanner plugin with reusable **Scan
Profiles**. Detects an installed [Nmap](https://nmap.org) binary, its
version, and — unlike every other tool plugin in this codebase — actually
executes real scans.

## Architecture

| File | Responsibility |
|---|---|
| `plugin.py` | Ties everything together: detection (inherited from `DetectionOnlyPlugin`), `build_command()`, real `execute()`, `parse()`, `normalize()`. |
| `models.py` | `ScanProfile`, `ProfileCategory`, `RiskLevel`, `AdvancedOptions` — pure data schemas. |
| `profile_manager.py` | Loads/validates/searches built-in profiles; full CRUD (create/edit/delete/duplicate/import/export) for custom ones. No DB or HTTP dependency. |
| `command_builder.py` | The **only** place a profile + target + user options become a real Nmap argv. Zero per-profile branching. |
| `parser.py` | Parses Nmap's `-oX` XML report (never its console text) into small dataclasses. |
| `normalizer.py` | Converts parsed output into `NormalizedOutput` (hosts/services/observations) — never a finding, never a CVSS score. |
| `validator.py` | Which target types Nmap can run against. |
| `profiles/*.json` | Built-in Scan Profiles. **Data, not code** — a new profile needs no code change anywhere in this package. |

## Scan Profiles are data

A profile describes *what* to scan (scan type flags, ports, NSE scripts,
risk level, estimated duration) as a JSON file, never a literal command
string. `command_builder.build_command()` combines a profile with the
target and optional per-job `AdvancedOptions` (timing, retries, a port
override, verbosity, extra raw arguments, script arguments) to produce the
actual argv — always ending in `-oX -` so the parser only ever reads
Nmap's structured XML.

Built-in profiles live in `profiles/` (read-only — ship with the plugin).
Custom profiles live under `data/profiles/nmap/` (outside this package, so
a plugin reinstall/upgrade never touches user data) and support full
create/edit/delete/duplicate/import/export. A built-in profile can never
be edited or deleted in place — duplicate it into an editable custom
profile first.

## Execution

`execute()` runs the built command for real via
`backend.plugins.sdk.process_runner.run_subprocess` (`asyncio.create_subprocess_exec`,
never `shell=True`) — the first plugin in this codebase whose `execute()`
doesn't unconditionally refuse. The execution engine (`backend.workers.manager`)
persists the resulting `RawToolOutput` (the raw XML), plus every `DiscoveredHost`/
`Service`/`Observation` the normalizer produced.

## Normalization produces no vulnerabilities

Per `.claude/CLAUDE.md` and this phase's explicit instruction, `normalize()`
only ever returns hosts, ports/services, and neutral script-output
observations — even for profiles wrapping an NSE script named
`smb-vuln-*` (e.g. MS17-010 Detection). This platform stores that script's
own raw output as an `Observation`; it never additionally scores, grades,
or promotes it to a `Finding`. Vulnerability correlation is a future
phase's job.

- **Detects:** `nmap` on `PATH` or common install directories, or a
  user-configured custom path.
- **Version:** `nmap --version`.
- **Supported targets:** IPv4, IPv6, CIDR, hostname.
