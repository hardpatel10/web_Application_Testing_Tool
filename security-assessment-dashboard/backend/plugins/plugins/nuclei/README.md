# Nuclei Plugin

Real, executing plugin for [Nuclei](https://github.com/projectdiscovery/nuclei),
ProjectDiscovery's template-based vulnerability scanner. Built to the
exact same architecture as the [Nmap plugin](../nmap/README.md) — the
reference implementation for a scanner plugin with reusable Scan
Profiles.

## Architecture

| File | Responsibility |
|---|---|
| `plugin.py` | Ties everything together: detection (inherited from `DetectionOnlyPlugin`), `build_command()`, real `execute()`, `parse()`, `normalize()`. |
| `models.py` | `ScanProfile`, `ProfileCategory`, `RiskLevel`, `AdvancedOptions` — pure data schemas. |
| `profile_manager.py` | Loads/validates/searches built-in profiles; full CRUD (create/edit/delete/duplicate/import/export) for custom ones. No DB or HTTP dependency. |
| `command_builder.py` | The **only** place a profile + target + user options become a real Nuclei argv. Zero per-profile branching. |
| `parser.py` | Parses Nuclei's `-jsonl` report (never its console text) into a small dataclass per finding. |
| `normalizer.py` | Converts parsed output into `NormalizedOutput` (host/observations) — never a finding, never a re-derived CVSS score. |
| `validator.py` | Which target types Nuclei can run against. |
| `profiles/*.json` | Built-in Scan Profiles. **Data, not code** — a new profile needs no code change anywhere in this package. |

## Scan Profiles are data

A profile describes *what* to scan (template paths/directories, tags,
excluded tags, a severity filter, risk level, estimated duration) as a
JSON file, never a literal command string. `command_builder.build_command()`
combines a profile with the target and optional per-job `AdvancedOptions`
(template/tag/severity overrides, rate limit, concurrency, retries, extra
raw arguments) to produce the actual argv — always ending in `-jsonl
-silent` so the parser only ever reads structured JSON lines, never
Nuclei's human-oriented console/progress text.

Nine built-in profiles ship in `profiles/`: **Quick** (a small, fast,
critical/high-only pass), **Default** (the recommended profile —
CVEs/vulnerabilities/exposures/misconfiguration/technologies/default-logins,
no severity filter), **Web**, **SSL**, **Exposure**, **CVE**,
**Misconfiguration**, **Technology**, and **Custom Templates** (a blank
baseline for Advanced Mode). Custom profiles live under
`data/profiles/nuclei/` and support full create/edit/delete/duplicate/
import/export, identically to Nmap's profile system.

## Execution

`execute()` runs the built command for real via
`backend.plugins.sdk.process_runner.run_subprocess` (`asyncio.create_subprocess_exec`,
never `shell=True`) — the exact same mechanism Nmap uses, since spawning a
subprocess is never plugin-specific. The execution engine
(`backend.workers.manager`) persists the resulting raw JSONL output, plus
the discovered host and every `Observation` the normalizer produced.

## Normalization produces no Findings

Per `.claude/CLAUDE.md`, `normalize()` only ever returns a host and neutral
observations — even though Nuclei's own JSON output already carries a
real severity, CVE/CWE ids, and a CVSS score. Those are real facts the
tool itself reported (never fabricated or re-derived) and are folded
verbatim into the observation's `detail` as structured text, so a
Correlation Engine rule (see `backend/correlation/rules/cross_tool_rules.py`)
can read them back out to build an actual scored `Finding` — turning a raw
result into a scored, correlated Finding is the Correlation Engine's job,
never this plugin's.

- **Detects:** `nuclei` on `PATH`, `~/go/bin` (its typical `go install` location), or a user-configured custom path.
- **Version:** `nuclei -version`.
- **Supported targets:** URL, hostname, domain, IPv4.
