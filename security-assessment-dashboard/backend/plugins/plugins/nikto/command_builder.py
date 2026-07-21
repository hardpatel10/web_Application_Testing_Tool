"""Turns a Scan Profile + target + user options into a real Nikto argv.

The only place a Scan Profile is ever converted into command-line flags.
Contains zero per-profile branching (no ``if profile.id == "ssl_scan"``
anywhere) — every profile-specific flag comes from the profile's own data
fields; this function only knows the generic *shape* of a Nikto command,
not what any particular profile means. New profiles need no code change
here at all, only a new JSON file under ``profiles/``.

Always appends ``-Format xml -o -`` (XML report to stdout) — never
negotiable, since the parser only ever reads Nikto's structured XML
output, never its human-oriented console text.
"""

from .models import AdvancedOptions, ScanProfile


def build_command(
    profile: ScanProfile,
    target_value: str,
    executable: str,
    *,
    port: str | None = None,
    use_ssl: bool = False,
    advanced: AdvancedOptions | None = None,
    default_timeout: int | None = None,
) -> list[str]:
    """Build the full Nikto argv for one job. Never executed here — only assembled.

    ``port``/``use_ssl`` are resolved target facts (e.g. from a URL's own
    scheme/port), not profile data -- a profile's ``arguments`` may still
    independently add its own ``-ssl`` (see the SSL Scan profile), Nikto
    tolerates the flag appearing twice.
    """
    advanced = advanced or AdvancedOptions()
    command: list[str] = [executable, "-h", target_value, *profile.arguments]

    if port:
        command += ["-p", port]
    if use_ssl:
        command.append("-ssl")

    tuning = advanced.tuning if advanced.tuning is not None else profile.tuning
    if tuning:
        command += ["-Tuning", tuning]

    plugins = advanced.plugins if advanced.plugins is not None else (profile.plugins or None)
    if plugins:
        command += ["-Plugins", ";".join(plugins)]

    timeout = advanced.timeout_seconds if advanced.timeout_seconds is not None else (profile.timeout_seconds or default_timeout)
    if timeout:
        command += ["-timeout", str(timeout)]

    command += list(advanced.additional_arguments)
    command += ["-Format", "xml", "-o", "-"]
    return command
