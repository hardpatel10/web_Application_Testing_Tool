# HTTPX Plugin

Detects an installed [HTTPX](https://github.com/projectdiscovery/httpx)
binary, its version, and builds (but never executes) the command that
would probe an HTTP target.

- **Detects:** `httpx` on `PATH`, `~/go/bin`, or a user-configured custom
  path.
- **Version:** `httpx -version`.
- **Supported targets:** URL, hostname, IPv4.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
