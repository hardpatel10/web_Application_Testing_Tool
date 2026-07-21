# FFUF Plugin

Detects an installed [FFUF](https://github.com/ffuf/ffuf) binary, its
version, and builds (but never executes) the command that would run a
fuzzing scan. Supports a configured `fuzzing` wordlist.

- **Detects:** `ffuf` on `PATH` or common install directories.
- **Version:** `ffuf -V`.
- **Supported targets:** URL (a `FUZZ` keyword is appended automatically
  if the target doesn't already contain one).
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
