"""Nmap plugin: the reference implementation for a scanner plugin with Scan Profiles.

Still extends ``DetectionOnlyPlugin`` for the identical-across-every-tool
parts (``metadata()``/``check_installation()``/``get_version()``/``health()``,
driven by ``BINARY_NAMES``/``VERSION_ARGS``/``VERSION_PATTERN``) but
overrides ``execute()`` for real — this is the first plugin in the
codebase whose ``execute()`` doesn't unconditionally refuse. ``build_command()``
never hardcodes a Scan Profile's flags: it looks up the profile named on
the execution context and hands it to ``command_builder.build_command()``,
which is the only place profile + target + user options become an argv.
"""

from pathlib import Path

from backend.core.config import PROJECT_ROOT
from backend.models.enums import RawOutputFormat, TargetType
from backend.plugins.models.config import PluginConfiguration
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.models.manifest import PluginManifest
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger, run_subprocess

from backend.plugins.models.normalized import NormalizedOutput

from .command_builder import build_command
from .models import AdvancedOptions
from .normalizer import normalize_nmap_output
from .parser import NmapScanResult, parse_nmap_output
from .profile_manager import ProfileManager
from .validator import resolve_nmap_target, validate_nmap_target

logger = get_plugin_logger("nmap")

#: Applied when a job doesn't specify a profile_id (e.g. an older client, or a
#: direct API call that predates Scan Profiles) — a reasonable, non-intrusive default.
DEFAULT_PROFILE_ID = "service_detection"

_PLUGIN_DIR = Path(__file__).resolve().parent
_BUILT_IN_PROFILES_DIR = _PLUGIN_DIR / "profiles"
_CUSTOM_PROFILES_DIR = PROJECT_ROOT / "data" / "profiles" / "nmap"


class NmapPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["nmap"]
    VERSION_ARGS = ["--version"]
    VERSION_PATTERN = r"Nmap version (\S+)"

    def __init__(self, manifest: PluginManifest, config: PluginConfiguration | None = None) -> None:
        super().__init__(manifest, config)
        self.profile_manager = ProfileManager(_BUILT_IN_PROFILES_DIR, _CUSTOM_PROFILES_DIR)

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_nmap_target(target_type, target_value)

    def prepare(self, context: PluginExecutionContext) -> None:
        context.output_directory.mkdir(parents=True, exist_ok=True)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        profile = self.profile_manager.get(context.profile_id or DEFAULT_PROFILE_ID)
        advanced = AdvancedOptions.model_validate(context.advanced_options) if context.advanced_options else None
        target = resolve_nmap_target(context.target_type, context.target_value)
        return build_command(
            profile,
            target,
            str(executable) if executable else "nmap",
            advanced=advanced,
            default_retries=self._config.retries,
            default_rate_limit=self._config.rate_limit,
        )

    async def execute(self, command: list[str], context: PluginExecutionContext) -> PluginRawOutput:
        logger.debug("Running: %s", " ".join(command))
        result = await run_subprocess(command, timeout_seconds=context.timeout_seconds)
        return PluginRawOutput(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.return_code,
            output_format=RawOutputFormat.XML,
        )

    def parse(self, raw_output: PluginRawOutput) -> NmapScanResult | None:
        return parse_nmap_output(raw_output)

    def normalize(self, parsed_output: NmapScanResult | None) -> NormalizedOutput:
        return normalize_nmap_output(parsed_output)

    def cleanup(self, context: PluginExecutionContext) -> None:
        return None
