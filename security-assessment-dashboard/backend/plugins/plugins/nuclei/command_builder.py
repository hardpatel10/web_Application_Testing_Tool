"""Turns a Scan Profile + target + user options into a real Nuclei argv.

The only place a Scan Profile is ever converted into command-line flags.
Contains zero per-profile branching (no ``if profile.id == "cve"``
anywhere) — every profile-specific flag comes from the profile's own data
fields; this function only knows the generic *shape* of a Nuclei command,
not what any particular profile means. New profiles need no code change
here at all, only a new JSON file under ``profiles/``.

Always appends ``-jsonl`` (JSON-lines results to stdout) and ``-silent``
(suppresses Nuclei's banner/progress noise so stdout is pure JSONL) --
never negotiable, since the parser only ever reads structured JSON lines,
never Nuclei's human-oriented console text.
"""

from .models import AdvancedOptions, ScanProfile


def build_command(
    profile: ScanProfile,
    target_value: str,
    executable: str,
    *,
    advanced: AdvancedOptions | None = None,
    default_rate_limit: int | None = None,
    default_retries: int | None = None,
) -> list[str]:
    """Build the full Nuclei argv for one job. Never executed here — only assembled."""
    advanced = advanced or AdvancedOptions()
    command: list[str] = [executable, "-u", target_value, *profile.arguments]

    templates = advanced.templates if advanced.templates is not None else profile.templates
    for template in templates:
        command += ["-t", template]

    tags = advanced.tags if advanced.tags is not None else profile.tags
    if tags:
        command += ["-tags", ",".join(tags)]

    exclude_tags = advanced.exclude_tags if advanced.exclude_tags is not None else profile.exclude_tags
    if exclude_tags:
        command += ["-etags", ",".join(exclude_tags)]

    severities = advanced.severities if advanced.severities is not None else profile.severities
    if severities:
        command += ["-severity", ",".join(severities)]

    rate_limit = advanced.rate_limit if advanced.rate_limit is not None else default_rate_limit
    if rate_limit:
        command += ["-rl", str(rate_limit)]

    if advanced.concurrency:
        command += ["-c", str(advanced.concurrency)]

    retries = advanced.retries if advanced.retries is not None else default_retries
    if retries is not None:
        command += ["-retries", str(retries)]

    command += list(advanced.additional_arguments)
    command += ["-jsonl", "-silent"]
    return command
