"""Nuclei plugin: template-based vulnerability detection with reusable Scan Profiles.

Follows the exact architecture Nmap established (Phase 7): still extends
``DetectionOnlyPlugin`` for the identical-across-every-tool parts
(``metadata()``/``check_installation()``/``get_version()``/``health()``),
overrides ``execute()`` for real via the shared ``run_subprocess`` SDK
helper, and never hardcodes a Scan Profile's flags in ``build_command()``
-- it looks up the profile named on the execution context and hands it to
``command_builder.build_command()``, the only place profile + target +
user options become an argv.
"""

from pathlib import Path

from backend.core.config import PROJECT_ROOT
from backend.models.enums import RawOutputFormat, TargetType
from backend.plugins.models.config import PluginConfiguration
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.models.manifest import PluginManifest
from backend.plugins.models.normalized import NormalizedOutput
from backend.plugins.sdk import DetectionOnlyPlugin, get_plugin_logger, run_subprocess

from .command_builder import build_command
from .models import AdvancedOptions
from .normalizer import normalize_nuclei_output
from .parser import NucleiScanResult, parse_nuclei_output
from .profile_manager import ProfileManager
from .validator import validate_nuclei_target

logger = get_plugin_logger("nuclei")

#: Applied when a job doesn't specify a profile_id -- Nuclei's own recommended,
#: production template set (CVEs/vulnerabilities/exposures/misconfiguration/technologies).
DEFAULT_PROFILE_ID = "default_scan"

_PLUGIN_DIR = Path(__file__).resolve().parent
_BUILT_IN_PROFILES_DIR = _PLUGIN_DIR / "profiles"
_CUSTOM_PROFILES_DIR = PROJECT_ROOT / "data" / "profiles" / "nuclei"


class NucleiPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["nuclei"]
    VERSION_ARGS = ["-version"]
    VERSION_PATTERN = r"v?(\d+\.\d+\.\d+)"

    def __init__(self, manifest: PluginManifest, config: PluginConfiguration | None = None) -> None:
        super().__init__(manifest, config)
        self.profile_manager = ProfileManager(_BUILT_IN_PROFILES_DIR, _CUSTOM_PROFILES_DIR)

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_nuclei_target(target_type, target_value)

    def prepare(self, context: PluginExecutionContext) -> None:
        context.output_directory.mkdir(parents=True, exist_ok=True)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        profile = self.profile_manager.get(context.profile_id or DEFAULT_PROFILE_ID)
        advanced = AdvancedOptions.model_validate(context.advanced_options) if context.advanced_options else None
        return build_command(
            profile,
            context.target_value,
            str(executable) if executable else "nuclei",
            advanced=advanced,
            default_rate_limit=self._config.rate_limit,
            default_retries=self._config.retries,
        )

    async def execute(self, command: list[str], context: PluginExecutionContext) -> PluginRawOutput:
        logger.debug("Running: %s", " ".join(command))
        result = await run_subprocess(command, timeout_seconds=context.timeout_seconds)
        return PluginRawOutput(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.return_code,
            output_format=RawOutputFormat.JSON,
        )

    def parse(self, raw_output: PluginRawOutput) -> NucleiScanResult | None:
        return parse_nuclei_output(raw_output)

    def normalize(self, parsed_output: NucleiScanResult | None) -> NormalizedOutput:
        return normalize_nuclei_output(parsed_output)

    def cleanup(self, context: PluginExecutionContext) -> None:
        return None
