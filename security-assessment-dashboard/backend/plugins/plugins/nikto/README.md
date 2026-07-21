# Nikto Plugin

Detects an installed [Nikto](https://cirt.net/Nikto2) binary, its version,
and builds (but never executes) the command that would run a web server
scan.

- **Detects:** `nikto`/`nikto.pl` on `PATH` or common install directories.
- **Version:** `nikto -Version`.
- **Supported targets:** URL, hostname.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
