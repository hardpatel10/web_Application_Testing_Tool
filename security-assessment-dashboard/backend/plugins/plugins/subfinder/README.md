# Subfinder Plugin

Detects an installed
[Subfinder](https://github.com/projectdiscovery/subfinder) binary, its
version, and builds (but never executes) the command that would run
subdomain discovery.

- **Detects:** `subfinder` on `PATH`, `~/go/bin`, or a user-configured
  custom path.
- **Version:** `subfinder -version`.
- **Supported targets:** domain.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
