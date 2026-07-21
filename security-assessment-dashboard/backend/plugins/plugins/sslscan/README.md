# SSLScan Plugin

Detects an installed [SSLScan](https://github.com/rbsec/sslscan) binary,
its version, and builds (but never executes) the command that would test
a target's TLS configuration.

- **Detects:** `sslscan` on `PATH` or common install directories.
- **Version:** `sslscan --version`.
- **Supported targets:** hostname, IPv4, URL.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
