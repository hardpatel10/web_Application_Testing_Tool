"""Turns a Scan Profile + target + user options into a real Nmap argv.

The only place a Scan Profile is ever converted into command-line flags.
Contains zero per-profile branching (no ``if profile.id == "tcp_full"``
anywhere) — every profile-specific flag comes from the profile's own data
fields; this function only knows the generic *shape* of an Nmap command,
not what any particular profile means. New profiles need no code change
here at all, only a new JSON file under ``profiles/``.

Always appends ``-oX -`` (XML report to stdout) — never negotiable, since
the parser only ever reads Nmap's structured XML output, never its
human-oriented console text.
"""

from .models import AdvancedOptions, ScanProfile


def build_command(
    profile: ScanProfile,
    target_value: str,
    executable: str,
    *,
    advanced: AdvancedOptions | None = None,
    default_retries: int | None = None,
    default_rate_limit: int | None = None,
) -> list[str]:
    """Build the full Nmap argv for one job. Never executed here — only assembled."""
    advanced = advanced or AdvancedOptions()
    command: list[str] = [executable, *profile.arguments]

    if advanced.timing is not None:
        command.append(f"-T{advanced.timing}")

    retries = advanced.retries if advanced.retries is not None else default_retries
    if retries is not None:
        command += ["--max-retries", str(retries)]

    if default_rate_limit:
        command += ["--min-rate", str(default_rate_limit)]

    if advanced.port_range:
        command += ["-p", advanced.port_range]
    elif advanced.top_ports:
        command += ["--top-ports", str(advanced.top_ports)]
    elif profile.required_ports:
        command += ["-p", profile.required_ports]

    if profile.required_scripts:
        command += ["--script", ",".join(profile.required_scripts)]

    script_args = {**profile.script_args, **advanced.script_args}
    if script_args:
        command += ["--script-args", ",".join(f"{key}={value}" for key, value in script_args.items())]

    if advanced.verbosity:
        command.append("-" + "v" * advanced.verbosity)

    command += list(advanced.additional_arguments)
    command += ["-oX", "-", target_value]
    return command
