"""Input/output shapes for a plugin's ``prepare()``/``build_command()``/``execute()``.

Constructed for real by :mod:`backend.workers.manager` (the execution
engine, Phase 6) for every job it runs. See ``backend/plugins/README.md``
for the full plugin lifecycle these flow through.
"""

from pathlib import Path

from pydantic import BaseModel, Field

from backend.models.enums import RawOutputFormat, TargetType


class PluginExecutionContext(BaseModel):
    """Everything a plugin needs to prepare, build, and run one invocation.

    ``profile_id``/``advanced_options`` (Phase 7) exist so a plugin with a
    reusable, data-driven Scan Profile system (Nmap is the reference
    implementation) can look up which profile a specific job was planned
    with and build the right command — sourced from the job's own
    ``ToolExecution.profile_id``/``advanced_options`` columns, not from the
    tool's shared, tool-wide ``PluginConfiguration``. Both are ``None`` for
    every plugin that doesn't have a profile system; a plugin that ignores
    them behaves exactly as before.
    """

    target_type: TargetType
    target_value: str
    output_directory: Path
    timeout_seconds: int = Field(gt=0)
    extra_arguments: list[str] = Field(default_factory=list)
    profile_id: str | None = None
    advanced_options: dict | None = None


class PluginRawOutput(BaseModel):
    """The raw, unparsed result of one plugin execution.

    ``output_format`` (Phase 7) tells the execution engine's generic
    ``RawToolOutput``-persistence step what format ``stdout`` actually is
    (e.g. Nmap's ``-oX -`` XML report on stdout) — the plugin that produced
    it is the only thing that knows this, so it is set by ``execute()``
    itself rather than guessed downstream.
    """

    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    output_file: Path | None = None
    output_format: RawOutputFormat = RawOutputFormat.TXT
