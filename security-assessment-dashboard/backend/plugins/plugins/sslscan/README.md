# SSLScan Plugin

Real, executing plugin for [SSLScan](https://github.com/rbsec/sslscan),
rbsec's TLS/SSL configuration scanner. Built to the exact same architecture
as the [Nmap](../nmap/README.md)/[Nikto](../nikto/README.md)/[Nuclei](../nuclei/README.md)
plugins -- the reference implementation for a scanner plugin with reusable
Scan Profiles.

## Architecture

| File | Responsibility |
|---|---|
| `plugin.py` | Ties everything together: detection (inherited from `DetectionOnlyPlugin`), `build_command()`, real `execute()`, `parse()`, `normalize()`. |
| `models.py` | `ScanProfile`, `ProfileCategory`, `RiskLevel`, `AdvancedOptions` -- pure data schemas. |
| `profile_manager.py` | Loads/validates/searches built-in profiles; full CRUD (create/edit/delete/duplicate/import/export) for custom ones. No DB or HTTP dependency. |
| `command_builder.py` | The **only** place a profile + resolved target + user options become a real SSLScan argv. Zero per-profile branching. |
| `validator.py` | Which target types SSLScan can run against, and `resolve_sslscan_target()` -- reduces any of them to the bare host/port/IP-version SSLScan's CLI needs. |
| `parser.py` | Parses SSLScan's `--xml=-` report (never its human-oriented console text) into small dataclasses (protocols/ciphers/groups/Heartbleed/certificates), field names verified against real `sslscan 2.1.5` output. |
| `normalizer.py` | Converts parsed output into `NormalizedOutput` (host + observations) -- never a Finding, never a re-derived severity. |
| `profiles/*.json` | Built-in Scan Profiles. **Data, not code** -- a new profile needs no code change anywhere in this package. |

## Scan Profiles are data

A profile describes *what* to test (fixed SSLScan flags, an optional
per-socket/`--connect` timeout, risk level, estimated duration) as a JSON
file, never a literal command string. `command_builder.build_command()`
combines a profile with the resolved target and optional per-job
`AdvancedOptions` (SNI override, forced IPv4/IPv6, port override, timeout
overrides, raw extra arguments) to produce the actual argv -- always
ending in `--no-colour --xml=-` so the parser only ever reads structured
XML, never SSLScan's human-oriented console/colour output.

Six built-in profiles ship in `profiles/`: **Default TLS Assessment** (the
recommended profile -- SSLScan's own balanced defaults), **Deep TLS
Assessment** (full certificate chain, cipher IDs, signature algorithms,
client-auth CAs, handshake timing, OCSP), **Certificate Analysis**
(certificate-only, cipher/group enumeration switched off), **Protocol
Enumeration** (which SSL/TLS versions are enabled, fastest), **Cipher
Enumeration** (every accepted cipher with IDs and IANA names), and
**Custom** (a blank baseline for Advanced Mode). Custom profiles live
under `data/profiles/sslscan/` and support full create/edit/delete/
duplicate/import/export, identically to Nmap's profile system.

## Execution

`execute()` runs the built command for real via
`backend.plugins.sdk.process_runner.run_subprocess` (`asyncio.create_subprocess_exec`,
never `shell=True`) -- the exact same mechanism every other real-execution
plugin uses. The execution engine (`backend.workers.manager`) persists the
resulting raw XML output, plus the discovered host and every `Observation`
the normalizer produced.

## Never run against a non-TLS service, automatically

Per the Assessment Pipeline brief, SSLScan itself has no opinion on
whether a target is actually TLS-enabled -- that decision is made once,
upstream, by `backend/pipeline/rules/web_rules.py`'s `HttpsServiceRule`
(the only pipeline rule that ever schedules it), after Nmap has already
confirmed the service looks like HTTPS/TLS. A host with no TLS-enabled
service gets an explicit `SKIPPED` pipeline job with the reason
`"Skipped by Pipeline: No TLS-enabled services discovered."`, never a
silently-omitted scan. A manual, user-initiated run against an arbitrary
target is the user's own responsibility, exactly like every other plugin.

## Normalization produces no Findings

Per `.claude/CLAUDE.md`, `normalize()` only ever returns a host and two
neutral observations per scanned endpoint (`source="sslscan-enum-ciphers"`
for protocols/ciphers/groups/Heartbleed/fallback/renegotiation/
compression, `source="sslscan-cert"` per certificate) -- even though
SSLScan's own XML already flags weak protocol/cipher strength and
self-signed/expired/not-yet-valid certificates. Those are real facts the
tool itself reported (never fabricated or re-derived) and are folded
verbatim into each observation's `detail` as structured text -- and only
ever stated when actually true (see `normalizer.py`'s own docstring for
why a false "not expired"/"SSLv2: disabled" line would corrupt the
Correlation Engine's plain substring matching). A Correlation Engine rule
(see `backend/correlation/rules/tls_rules.py`, which already reads the
equivalent `ssl-cert`/`ssl-enum-ciphers` facts Nmap's own NSE scripts
produce) reads these `sslscan-*` observations back out using the exact
same rules -- turning a raw result into a scored, correlated Finding,
possibly backed by evidence from both Nmap and SSLScan at once, is the
Correlation Engine's job, never this plugin's.

- **Detects:** `sslscan` on `PATH` or common install directories.
- **Version:** `sslscan --version`.
- **Supported targets:** hostname, domain, IPv4, IPv6, URL.
