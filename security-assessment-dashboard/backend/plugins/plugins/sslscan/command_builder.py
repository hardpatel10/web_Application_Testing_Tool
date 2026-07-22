"""Turns a Scan Profile + resolved target + user options into a real SSLScan argv.

The only place a Scan Profile is ever converted into command-line flags.
Contains zero per-profile branching (no ``if profile.id == "cipher_enumeration"``
anywhere) -- every profile-specific flag comes from the profile's own data
fields; this function only knows the generic *shape* of an SSLScan command,
not what any particular profile means. New profiles need no code change
here at all, only a new JSON file under ``profiles/``.

Always appends ``--no-colour --xml=-`` (clean XML report to stdout) --
never negotiable, since the parser only ever reads SSLScan's structured
XML, never its human-oriented console text.
"""

from .models import AdvancedOptions, ScanProfile


def _host_argument(host: str, port: int | None, ip_version: str | None) -> str:
    """SSLScan takes ``host``, ``host:port``, or a bracketed ``[ipv6]``/``[ipv6]:port``."""
    is_ipv6 = ip_version == "6" or (":" in host and not host.startswith("["))
    bare = f"[{host}]" if is_ipv6 else host
    return f"{bare}:{port}" if port else bare


def build_command(
    profile: ScanProfile,
    host: str,
    executable: str,
    *,
    port: int | None = None,
    ip_version: str | None = None,
    advanced: AdvancedOptions | None = None,
    default_timeout: int | None = None,
) -> list[str]:
    """Build the full SSLScan argv for one job. Never executed here -- only assembled."""
    advanced = advanced or AdvancedOptions()
    command: list[str] = [executable, *profile.arguments]

    resolved_ip_version = advanced.ip_version if advanced.ip_version is not None else ip_version
    if resolved_ip_version == "4":
        command.append("--ipv4")
    elif resolved_ip_version == "6":
        command.append("--ipv6")

    if advanced.sni_name:
        command.append(f"--sni-name={advanced.sni_name}")

    timeout = advanced.timeout_seconds if advanced.timeout_seconds is not None else (profile.timeout_seconds or default_timeout)
    if timeout:
        command.append(f"--timeout={timeout}")

    connect_timeout = (
        advanced.connect_timeout_seconds if advanced.connect_timeout_seconds is not None else profile.connect_timeout_seconds
    )
    if connect_timeout:
        command.append(f"--connect-timeout={connect_timeout}")

    command += list(advanced.additional_arguments)
    command += ["--no-colour", "--xml=-"]

    resolved_port = advanced.port if advanced.port is not None else port
    command.append(_host_argument(host, resolved_port, resolved_ip_version))
    return command
