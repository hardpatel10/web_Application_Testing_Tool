# Nikto Plugin

Real, executing plugin for [Nikto](https://cirt.net/Nikto2), a web server
security scanner. Built to the exact same architecture as the [Nmap
plugin](../nmap/README.md) — the reference implementation for a scanner
plugin with reusable Scan Profiles.

## Architecture

| File | Responsibility |
|---|---|
| `plugin.py` | Ties everything together: detection (inherited from `DetectionOnlyPlugin`), `build_command()`, real `execute()`, `parse()`, `normalize()`. |
| `models.py` | `ScanProfile`, `ProfileCategory`, `RiskLevel`, `AdvancedOptions` — pure data schemas. |
| `profile_manager.py` | Loads/validates/searches built-in profiles; full CRUD (create/edit/delete/duplicate/import/export) for custom ones. No DB or HTTP dependency. |
| `command_builder.py` | The **only** place a profile + target + user options become a real Nikto argv. Zero per-profile branching. |
| `parser.py` | Parses Nikto's `-Format xml` report (never its console text) into small dataclasses. |
| `normalizer.py` | Converts parsed output into `NormalizedOutput` (hosts/observations) — never a finding, never a CVSS score. |
| `validator.py` | Which target types Nikto can run against, and resolving a URL target into host/port/`-ssl` facts. |
| `profiles/*.json` | Built-in Scan Profiles. **Data, not code** — a new profile needs no code change anywhere in this package. |

## Scan Profiles are data

A profile describes *what* to check (`-Tuning` category codes, `-Plugins`
names, any other fixed flag, risk level, estimated duration) as a JSON
file, never a literal command string. `command_builder.build_command()`
combines a profile with the target and optional per-job `AdvancedOptions`
(tuning/plugins/timeout overrides, extra raw arguments) to produce the
actual argv — always ending in `-Format xml -o -` so the parser only ever
reads Nikto's structured XML.

Nine built-in profiles ship in `profiles/`: **Quick Scan** (fast,
low-noise), **Default Scan** (the recommended profile — Nikto's full
standard check set, no tuning restriction), **Full Scan** (adds
exhaustive CGI directory enumeration), **SSL Scan**, **Headers**,
**Interesting Files**, **CGI**, **Misconfiguration Scan**, and **Custom
Scan** (a blank baseline for Advanced Mode). Custom profiles live under
`data/profiles/nikto/` and support full create/edit/delete/duplicate/
import/export, identically to Nmap's profile system.

## Execution

`execute()` runs the built command for real via
`backend.plugins.sdk.process_runner.run_subprocess` (`asyncio.create_subprocess_exec`,
never `shell=True`) — the exact same mechanism Nmap uses, since spawning a
subprocess is never plugin-specific. The execution engine
(`backend.workers.manager`) persists the resulting raw XML output, plus
every `DiscoveredHost`/`Observation` the normalizer produced.

## Normalization produces no vulnerabilities

Per `.claude/CLAUDE.md`, `normalize()` only ever returns a host and neutral
observations — even when Nikto's own finding text references a real OSVDB
id, CVE, or CWE. Those references are extracted from Nikto's own text
(via regex, never guessed) and folded into the observation's `detail` as
plain facts, the same "record what the tool said, verbatim" discipline
Nmap's normalizer already applies to NSE script output. Turning an
observation into a scored, correlated `Finding` remains the Correlation
Engine's job, not this plugin's.

- **Detects:** `nikto`/`nikto.pl` on `PATH` or common install directories, or a user-configured custom path.
- **Version:** `nikto -Version`.
- **Supported targets:** URL, hostname, domain (Nikto scans over HTTP/HTTPS, resolved from the target's own scheme/port when given a URL).
