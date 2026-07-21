# Installing Security Tools on Linux

The runtime platform for this application is **Linux only** (see `.claude/CLAUDE.md`). The backend never installs a tool automatically — a plugin only *detects* whether a tool's binary is on `PATH` (or in a common install directory) and reports "Not Installed" with a message pointing back to this file if it can't find one. Install the tool yourself, then re-check via the Tools page (or `GET /tools`) — no restart is required, detection re-runs on every health check.

Every command below is a normal Linux shell command, not something Claude Code or the application executes on your behalf.

## Detection

`backend/plugins/sdk/detection_helpers.py` looks for each tool's binary in this order:

1. `PATH` (`shutil.which`)
2. `~/go/bin` (the default for `go install`, used by most tools below)
3. `~/.local/bin`
4. `/usr/local/bin`, `/usr/local/sbin`
5. `/usr/bin`, `/usr/sbin`
6. `/opt`
7. `/snap/bin`

As long as a tool ends up on `PATH` (the normal outcome of any package-manager install, or of adding `~/go/bin` to `PATH` after a `go install`), detection finds it with no extra configuration.

## Per-tool installation

| Tool | apt (Debian/Ubuntu/Kali) | dnf (Fedora/RHEL) | pacman (Arch) | Official / upstream method |
|---|---|---|---|---|
| [nmap](https://nmap.org) | `sudo apt install nmap` | `sudo dnf install nmap` | `sudo pacman -S nmap` | https://nmap.org/download.html |
| [nuclei](https://github.com/projectdiscovery/nuclei) | — | — | — | `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest` |
| [nikto](https://github.com/sullo/nikto) | `sudo apt install nikto` | `sudo dnf install nikto` | AUR: `yay -S nikto` | `git clone https://github.com/sullo/nikto.git` |
| [whatweb](https://github.com/urbanadventurer/WhatWeb) | `sudo apt install whatweb` | not packaged; use upstream | AUR: `yay -S whatweb` | `git clone https://github.com/urbanadventurer/WhatWeb.git` (Ruby; `bundle install`) |
| [subfinder](https://github.com/projectdiscovery/subfinder) | — | — | AUR: `yay -S subfinder` | `go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest` |
| [sslscan](https://github.com/rbsec/sslscan) | `sudo apt install sslscan` | `sudo dnf install sslscan` | `sudo pacman -S sslscan` | https://github.com/rbsec/sslscan |
| [naabu](https://github.com/projectdiscovery/naabu) | — | — | AUR: `yay -S naabu` | `go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest` (needs `libpcap-dev`) |
| [katana](https://github.com/projectdiscovery/katana) | — | — | AUR: `yay -S katana` | `go install github.com/projectdiscovery/katana/cmd/katana@latest` |
| [httpx](https://github.com/projectdiscovery/httpx) | — | — | AUR: `yay -S httpx` | `go install github.com/projectdiscovery/httpx/cmd/httpx@latest` |
| [gobuster](https://github.com/OJ/gobuster) | `sudo apt install gobuster` | `sudo dnf install gobuster` | `sudo pacman -S gobuster` | `go install github.com/OJ/gobuster/v3@latest` |
| [ffuf](https://github.com/ffuf/ffuf) | `sudo apt install ffuf` | `sudo dnf install ffuf` | `sudo pacman -S ffuf` | `go install github.com/ffuf/ffuf/v2@latest` |
| [feroxbuster](https://github.com/epi052/feroxbuster) | `sudo apt install feroxbuster` | — | AUR: `yay -S feroxbuster` | `curl -sL https://raw.githubusercontent.com/epi052/feroxbuster/main/install-nix.sh \| bash` |
| [dnsx](https://github.com/projectdiscovery/dnsx) | — | — | AUR: `yay -S dnsx` | `go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest` |
| [dirsearch](https://github.com/maurosoria/dirsearch) | `pip install dirsearch` | `pip install dirsearch` | `sudo pacman -S dirsearch` | `pip install dirsearch` or `git clone https://github.com/maurosoria/dirsearch.git` |
| [amass](https://github.com/owasp-amass/amass) | `sudo apt install amass` | `sudo dnf install amass` | `sudo pacman -S amass` | `go install github.com/owasp-amass/amass/v4/...@master` or `snap install amass` |

Notes:

- Package availability varies by distro version — the "official / upstream method" column always works and is the most current.
- The ProjectDiscovery tools (`nuclei`, `subfinder`, `naabu`, `katana`, `httpx`, `dnsx`) are Go binaries; `go install ...@latest` puts them in `~/go/bin`, which detection already searches. Make sure `~/go/bin` is on `PATH` for anything else that shells out to them directly.
- `whatweb` and `dirsearch` are Ruby/Python tools respectively; installing via `pip`/`gem`/git clone is normal for them and still produces a `PATH`-resolvable binary once installed correctly.
- None of these commands are run by the application — install them yourself on the Linux host, then let the Tools page confirm detection.

## Adding a new tool

When a future phase integrates a new tool, add a row to the table above (or a short section if the tool needs non-trivial setup) as part of that phase's own documentation update — this is required by `.claude/CLAUDE.md`'s runtime-platform rules, not optional polish.
