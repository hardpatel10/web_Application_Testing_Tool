# DNSx Plugin

Detects an installed [DNSx](https://github.com/projectdiscovery/dnsx)
binary, its version, and builds (but never executes) the command that
would run DNS resolution/enumeration.

- **Detects:** `dnsx` on `PATH`, `~/go/bin`, or a user-configured custom
  path.
- **Version:** `dnsx -version`.
- **Supported targets:** domain, hostname.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
