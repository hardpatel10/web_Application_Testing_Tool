# WhatWeb Plugin

Detects an installed [WhatWeb](https://github.com/urbanadventurer/WhatWeb)
binary, its version, and builds (but never executes) the command that
would fingerprint a website's technologies.

- **Detects:** `whatweb` on `PATH` or common install directories.
- **Version:** `whatweb --version`.
- **Supported targets:** URL, hostname.
- **Never executes a scan** — `execute()` raises; this phase is detection
  and configuration only.
