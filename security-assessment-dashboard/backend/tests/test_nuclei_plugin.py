"""Tests for the Nuclei plugin: profiles, command generation, JSONL parsing, normalization.

Profile loading/validation, command generation, and JSONL parsing/
normalization are pure and fully host-agnostic (no real ``nuclei`` binary
needed). The real-execution test is skipped outright if ``nuclei`` isn't
actually installed on the machine running the tests -- the same
host-agnostic philosophy ``test_nmap_plugin.py`` already uses.
"""

import shutil
from pathlib import Path

import pytest

from backend.core.config import get_settings
from backend.models.enums import HostState, TargetType
from backend.plugins.exceptions import PluginNotFoundError as FrameworkPluginNotFoundError
from backend.plugins.manager.plugin_manager import get_plugin_manager
from backend.plugins.models.execution import PluginExecutionContext
from backend.plugins.models.normalized import NormalizedOutput
from backend.plugins.plugins.nuclei.command_builder import build_command
from backend.plugins.plugins.nuclei.models import AdvancedOptions, ProfileCategory, RiskLevel, ScanProfile
from backend.plugins.plugins.nuclei.normalizer import normalize_nuclei_output
from backend.plugins.plugins.nuclei.parser import NucleiFinding, NucleiScanResult, parse_nuclei_output
from backend.plugins.plugins.nuclei.profile_manager import ProfileManager, ProfileNotFoundError, ProfileValidationError
from backend.plugins.plugins.nuclei.validator import validate_nuclei_target
from backend.plugins.sdk import PluginRawOutput

NUCLEI_INSTALLED = shutil.which("nuclei") is not None


def _get_nuclei_plugin():
    manager = get_plugin_manager(get_settings().plugins_dir)
    manager.discover_and_register()
    return manager.get_plugin("nuclei")


# -- Built-in profile loading -------------------------------------------------


def test_all_built_in_profiles_load_and_validate() -> None:
    plugin = _get_nuclei_plugin().instance
    profiles = plugin.profile_manager.list_profiles()
    assert len(profiles) == 9
    assert all(profile.built_in for profile in profiles)


def test_profile_categories_cover_the_requested_taxonomy() -> None:
    plugin = _get_nuclei_plugin().instance
    categories = {profile.category for profile in plugin.profile_manager.list_profiles()}
    assert categories == set(ProfileCategory)


def test_default_profile_is_default_scan() -> None:
    from backend.plugins.plugins.nuclei.plugin import DEFAULT_PROFILE_ID

    plugin = _get_nuclei_plugin().instance
    profile = plugin.profile_manager.get(DEFAULT_PROFILE_ID)
    assert profile.id == "default_scan"
    assert "http/cves/" in profile.templates


def test_search_filters_by_category_and_risk() -> None:
    plugin = _get_nuclei_plugin().instance
    cve_profiles = plugin.profile_manager.search(category=ProfileCategory.CVE)
    assert all(profile.category == ProfileCategory.CVE for profile in cve_profiles)
    assert any(profile.id == "cve" for profile in cve_profiles)


# -- Command builder -----------------------------------------------------------


def _profile(**overrides) -> ScanProfile:
    defaults = dict(
        id="test_profile", name="Test", description="d", category=ProfileCategory.DEFAULT,
        supported_targets=[TargetType.URL],
    )
    defaults.update(overrides)
    return ScanProfile(**defaults)


def test_command_builder_applies_templates_tags_and_severity_from_profile() -> None:
    profile = _profile(templates=["cves/"], tags=["cve"], exclude_tags=["dos"], severities=["critical"])
    command = build_command(profile, "https://example.com", "nuclei")
    assert command[:3] == ["nuclei", "-u", "https://example.com"]
    assert "-t" in command and command[command.index("-t") + 1] == "cves/"
    assert "-tags" in command and command[command.index("-tags") + 1] == "cve"
    assert "-etags" in command and command[command.index("-etags") + 1] == "dos"
    assert "-severity" in command and command[command.index("-severity") + 1] == "critical"


def test_command_builder_advanced_options_override_profile() -> None:
    profile = _profile(severities=["low"])
    advanced = AdvancedOptions(severities=["critical", "high"], concurrency=25)
    command = build_command(profile, "https://example.com", "nuclei", advanced=advanced)
    assert command[command.index("-severity") + 1] == "critical,high"
    assert "-c" in command and command[command.index("-c") + 1] == "25"


def test_command_builder_rate_limit_and_retries_fall_back_to_tool_defaults() -> None:
    profile = _profile()
    command = build_command(profile, "https://example.com", "nuclei", default_rate_limit=100, default_retries=2)
    assert "-rl" in command and command[command.index("-rl") + 1] == "100"
    assert "-retries" in command and command[command.index("-retries") + 1] == "2"


def test_command_builder_always_ends_with_jsonl_and_silent() -> None:
    profile = _profile()
    command = build_command(profile, "https://example.com", "nuclei")
    assert command[-2:] == ["-jsonl", "-silent"]


def test_plugin_build_command_uses_default_profile_when_none_specified() -> None:
    plugin = _get_nuclei_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.URL, target_value="https://example.com", output_directory=Path("."), timeout_seconds=60
    )
    command = plugin.build_command(context)
    assert "-u" in command and "https://example.com" in command


def test_plugin_build_command_raises_for_unknown_profile() -> None:
    """Catches the framework's stable PluginNotFoundError, not this module's own ProfileNotFoundError
    import -- see backend/plugins/plugins/nmap/README.md's equivalent test for the full explanation
    of why the plugin's synthetically-loaded module identity makes the direct import not match."""
    plugin = _get_nuclei_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.URL, target_value="https://example.com", output_directory=Path("."),
        timeout_seconds=60, profile_id="does-not-exist",
    )
    with pytest.raises(FrameworkPluginNotFoundError):
        plugin.build_command(context)


# -- Target validation ---------------------------------------------------------


@pytest.mark.parametrize(
    ("target_type", "target_value", "expected"),
    [
        (TargetType.URL, "https://example.com/path", True),
        (TargetType.HOSTNAME, "example.com", True),
        (TargetType.DOMAIN, "example.com", True),
        (TargetType.IPV4, "127.0.0.1", True),
        (TargetType.CIDR, "10.0.0.0/24", False),
    ],
)
def test_validate_target(target_type: TargetType, target_value: str, expected: bool) -> None:
    assert validate_nuclei_target(target_type, target_value) is expected


# -- Parser -----------------------------------------------------------------------

_SAMPLE_JSONL = (
    '{"template-id":"CVE-2021-41773","info":{"name":"Apache 2.4.49 - Path Traversal","severity":"critical",'
    '"description":"Apache 2.4.49 path traversal and RCE","tags":["cve","cve2021","apache","rce"],'
    '"reference":["https://nvd.nist.gov/vuln/detail/CVE-2021-41773"],'
    '"classification":{"cve-id":["CVE-2021-41773"],"cwe-id":["CWE-22"],"cvss-score":9.8}},'
    '"type":"http","host":"https://example.com","ip":"93.184.216.34",'
    '"matched-at":"https://example.com/icons/.%2e/%2e%2e/etc/passwd","timestamp":"2024-01-01T00:00:00Z",'
    '"matcher-name":"path-traversal"}\n'
    '{malformed json line should be skipped, not crash the whole parse}\n'
    '{"template-id":"tech-detect","info":{"name":"Technology Detection","severity":"info","tags":["tech"]},'
    '"type":"http","host":"https://example.com","matched-at":"https://example.com"}\n'
)


def test_parse_extracts_every_valid_finding_and_skips_malformed_lines() -> None:
    raw = PluginRawOutput(stdout=_SAMPLE_JSONL, exit_code=0)
    result = parse_nuclei_output(raw)
    assert result is not None
    assert len(result.findings) == 2
    cve_finding = result.findings[0]
    assert cve_finding.template_id == "CVE-2021-41773"
    assert cve_finding.severity == "critical"
    assert cve_finding.cve_ids == ["CVE-2021-41773"]
    assert cve_finding.cwe_ids == ["CWE-22"]
    assert cve_finding.cvss_score == 9.8


def test_parse_handles_empty_stdout() -> None:
    raw = PluginRawOutput(stdout="", exit_code=0)
    assert parse_nuclei_output(raw) is None


def test_parse_handles_no_findings_at_all() -> None:
    raw = PluginRawOutput(stdout="\n\n", exit_code=0)
    assert parse_nuclei_output(raw) is None


# -- Normalizer ----------------------------------------------------------------------


def test_normalize_folds_real_severity_cve_cwe_cvss_into_detail() -> None:
    raw = PluginRawOutput(stdout=_SAMPLE_JSONL, exit_code=0)
    normalized = normalize_nuclei_output(parse_nuclei_output(raw))
    assert isinstance(normalized, NormalizedOutput)
    assert len(normalized.hosts) == 1
    host = normalized.hosts[0]
    assert host.hostname == "example.com"
    assert host.addresses[0].ip_address == "93.184.216.34"
    assert host.state == HostState.UP

    cve_observation = normalized.observations[0]
    assert cve_observation.title == "Apache 2.4.49 - Path Traversal"
    assert "Severity: critical" in cve_observation.detail
    assert "CVE: CVE-2021-41773" in cve_observation.detail
    assert "CWE: CWE-22" in cve_observation.detail
    assert "CVSS: 9.8" in cve_observation.detail
    assert cve_observation.observation_type == "CVE-2021-41773"


def test_normalize_never_fabricates_a_finding_only_observations() -> None:
    """Structural check: NormalizedObservation has no severity/CVSS field of its own --
    real facts live in .detail text only, never a fabricated structured column."""
    raw = PluginRawOutput(stdout=_SAMPLE_JSONL, exit_code=0)
    normalized = normalize_nuclei_output(parse_nuclei_output(raw))
    for observation in normalized.observations:
        assert not hasattr(observation, "severity")
        assert not hasattr(observation, "cvss_score")


def test_normalize_handles_no_parsed_output() -> None:
    assert normalize_nuclei_output(None) == NormalizedOutput()


def test_normalize_extracts_bare_ip_target_correctly() -> None:
    raw = PluginRawOutput(
        stdout='{"template-id":"t","info":{"name":"n","severity":"low"},"type":"http","host":"93.184.216.34"}\n',
        exit_code=0,
    )
    normalized = normalize_nuclei_output(parse_nuclei_output(raw))
    assert normalized.hosts[0].hostname is None
    assert normalized.hosts[0].addresses[0].ip_address == "93.184.216.34"


# -- Custom profile CRUD --------------------------------------------------------


def test_custom_profile_crud_lifecycle(tmp_path: Path) -> None:
    manager = ProfileManager(Path(__file__).resolve().parent.parent / "plugins" / "plugins" / "nuclei" / "profiles", tmp_path)
    created = manager.create_custom(
        {"id": "my_custom", "name": "Mine", "description": "d", "category": "custom", "supported_targets": ["url"]}
    )
    assert created.built_in is False
    manager.delete_custom("my_custom")
    with pytest.raises(ProfileNotFoundError):
        manager.get("my_custom")


def test_built_in_profile_cannot_be_edited_or_deleted(tmp_path: Path) -> None:
    manager = ProfileManager(Path(__file__).resolve().parent.parent / "plugins" / "plugins" / "nuclei" / "profiles", tmp_path)
    with pytest.raises(ProfileValidationError):
        manager.delete_custom("default_scan")


# -- Real execution (skipped unless nuclei is actually installed) --------------


@pytest.mark.skipif(not NUCLEI_INSTALLED, reason="nuclei is not installed on this machine")
@pytest.mark.asyncio
async def test_real_execute_against_example_com_produces_real_output(tmp_path: Path) -> None:
    plugin = _get_nuclei_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.URL, target_value="https://example.com", output_directory=tmp_path,
        timeout_seconds=120, profile_id="technology",
    )
    plugin.prepare(context)
    command = plugin.build_command(context)
    raw_output = await plugin.execute(command, context)
    assert raw_output.exit_code == 0
    parsed = plugin.parse(raw_output)
    normalized = plugin.normalize(parsed)
    assert isinstance(normalized, NormalizedOutput)
