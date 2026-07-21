# Naabu Plugin

Detects an installed [Naabu](https://github.com/projectdiscovery/naabu)
binary, its version, and builds (but never executes) the command that
would run a port scan.

- **Detects:** `naabu` on `PATH`, `~/go/bin`, or a user-configured custom
  path.
- **Version:** `naabu -version`.
- **Supported targets:** IPv4, IPv6, CIDR, hostname.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
