"""SSLScan plugin: TLS/SSL configuration assessment with reusable Scan Profiles.

Follows the exact architecture Nmap established (Phase 7): still extends
``DetectionOnlyPlugin`` for the identical-across-every-tool parts
(``metadata()``/``check_installation()``/``get_version()``/``health()``),
overrides ``execute()`` for real via the shared ``run_subprocess`` SDK
helper, and never hardcodes a Scan Profile's flags in ``build_command()``
-- it looks up the profile named on the execution context, resolves the
target to what SSLScan's CLI actually needs (bare host/port/IP version),
and hands both to ``command_builder.build_command()``, the only place
profile + target + user options become an argv.

Per the Assessment Pipeline brief, SSLScan itself never decides whether a
target is actually TLS-enabled -- that decision is made once, upstream, by
``backend/pipeline/rules/web_rules.py`` (only ``HttpsServiceRule`` ever
schedules it) before this plugin ever runs. Manual, user-initiated runs
are the user's own responsibility, exactly like every other plugin in this
codebase.
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
from .normalizer import normalize_sslscan_output
from .parser import SslscanScanResult, parse_sslscan_output
from .profile_manager import ProfileManager
from .validator import resolve_sslscan_target, validate_sslscan_target

logger = get_plugin_logger("sslscan")

#: Applied when a job doesn't specify a profile_id -- SSLScan's own sensible
#: defaults (every protocol/cipher/group/Heartbleed/fallback/renegotiation/
#: compression check, plus the certificate).
DEFAULT_PROFILE_ID = "default_scan"

_PLUGIN_DIR = Path(__file__).resolve().parent
_BUILT_IN_PROFILES_DIR = _PLUGIN_DIR / "profiles"
_CUSTOM_PROFILES_DIR = PROJECT_ROOT / "data" / "profiles" / "sslscan"


class SslscanPlugin(DetectionOnlyPlugin):
    BINARY_NAMES = ["sslscan"]
    VERSION_ARGS = ["--version"]
    VERSION_PATTERN = r"(\d+\.\d+\.\d+)"

    def __init__(self, manifest: PluginManifest, config: PluginConfiguration | None = None) -> None:
        super().__init__(manifest, config)
        self.profile_manager = ProfileManager(_BUILT_IN_PROFILES_DIR, _CUSTOM_PROFILES_DIR)

    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        return validate_sslscan_target(target_type, target_value)

    def prepare(self, context: PluginExecutionContext) -> None:
        context.output_directory.mkdir(parents=True, exist_ok=True)

    def build_command(self, context: PluginExecutionContext) -> list[str]:
        executable = self.resolve_executable()
        profile = self.profile_manager.get(context.profile_id or DEFAULT_PROFILE_ID)
        advanced = AdvancedOptions.model_validate(context.advanced_options) if context.advanced_options else None
        resolved = resolve_sslscan_target(context.target_type, context.target_value)
        return build_command(
            profile,
            resolved.host,
            str(executable) if executable else "sslscan",
            port=resolved.port,
            ip_version=resolved.ip_version,
            advanced=advanced,
            default_timeout=self._config.default_timeout_seconds,
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

    def parse(self, raw_output: PluginRawOutput) -> SslscanScanResult | None:
        return parse_sslscan_output(raw_output)

    def normalize(self, parsed_output: SslscanScanResult | None) -> NormalizedOutput:
        return normalize_sslscan_output(parsed_output)

    def cleanup(self, context: PluginExecutionContext) -> None:
        return None
