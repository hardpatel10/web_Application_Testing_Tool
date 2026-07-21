# Feroxbuster Plugin

Detects an installed [Feroxbuster](https://github.com/epi052/feroxbuster)
binary, its version, and builds (but never executes) the command that
would run a recursive content-discovery scan. Supports a configured
`directory` wordlist.

- **Detects:** `feroxbuster` on `PATH` or common install directories.
- **Version:** `feroxbuster --version`.
- **Supported targets:** URL.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
