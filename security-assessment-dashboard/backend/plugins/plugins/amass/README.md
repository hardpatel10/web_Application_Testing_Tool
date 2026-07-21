# Amass Plugin

Detects an installed [OWASP Amass](https://github.com/owasp-amass/amass)
binary, its version, and builds (but never executes) the command that
would run attack-surface/subdomain enumeration. Supports a configured
`subdomains` wordlist for brute-force mode.

- **Detects:** `amass` on `PATH` or common install directories.
- **Version:** `amass -version`.
- **Supported targets:** domain.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
