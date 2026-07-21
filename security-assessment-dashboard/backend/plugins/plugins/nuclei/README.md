# Nuclei Plugin

Detects an installed [Nuclei](https://github.com/projectdiscovery/nuclei)
binary, its version, and builds (but never executes) the command that
would run a template-based scan.

- **Detects:** `nuclei` on `PATH`, `~/go/bin` (its typical `go install`
  location), or a user-configured custom path.
- **Version:** `nuclei -version`.
- **Supported targets:** URL, hostname, IPv4.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
