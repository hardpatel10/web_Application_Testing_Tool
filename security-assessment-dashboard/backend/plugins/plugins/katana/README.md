# Katana Plugin

Detects an installed [Katana](https://github.com/projectdiscovery/katana)
binary, its version, and builds (but never executes) the command that
would crawl a target.

- **Detects:** `katana` on `PATH`, `~/go/bin`, or a user-configured custom
  path.
- **Version:** `katana -version`.
- **Supported targets:** URL.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
