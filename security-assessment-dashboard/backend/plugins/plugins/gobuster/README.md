# Gobuster Plugin

Detects an installed [Gobuster](https://github.com/OJ/gobuster) binary,
its version, and builds (but never executes) the command that would run a
directory brute-force scan. Supports a configured `directory` wordlist.

- **Detects:** `gobuster` on `PATH` or common install directories.
- **Version:** `gobuster version` (a subcommand, not a flag).
- **Supported targets:** URL.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
