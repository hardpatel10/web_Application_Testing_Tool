# Dirsearch Plugin

Detects an installed [Dirsearch](https://github.com/maurosoria/dirsearch)
binary, its version, and builds (but never executes) the command that
would run a path brute-force scan. Supports a configured `directory`
wordlist.

- **Detects:** `dirsearch` on `PATH` or common install directories.
- **Version:** `dirsearch --version`.
- **Supported targets:** URL.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
