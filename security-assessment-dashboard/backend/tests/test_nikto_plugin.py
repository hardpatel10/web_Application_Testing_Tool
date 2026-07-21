"""Tests for the Nikto plugin: profiles, command generation, XML parsing, normalization.

Profile loading/validation, command generation, and XML parsing/
normalization are pure and fully host-agnostic (no real ``nikto`` binary
needed). The real-execution test is skipped outright if ``nikto`` isn't
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
from backend.plugins.plugins.nikto.command_builder import build_command
from backend.plugins.plugins.nikto.models import AdvancedOptions, ProfileCategory, RiskLevel, ScanProfile
from backend.plugins.plugins.nikto.normalizer import normalize_nikto_output
from backend.plugins.plugins.nikto.parser import NiktoFinding, NiktoHost, NiktoScanResult, parse_nikto_output
from backend.plugins.plugins.nikto.profile_manager import ProfileManager, ProfileNotFoundError, ProfileValidationError
from backend.plugins.plugins.nikto.validator import resolve_nikto_target, validate_nikto_target
from backend.plugins.sdk import PluginRawOutput

NIKTO_INSTALLED = shutil.which("nikto") is not None or shutil.which("nikto.pl") is not None


def _get_nikto_plugin():
    manager = get_plugin_manager(get_settings().plugins_dir)
    manager.discover_and_register()
    return manager.get_plugin("nikto")


# -- Built-in profile loading -------------------------------------------------


def test_all_built_in_profiles_load_and_validate() -> None:
    plugin = _get_nikto_plugin().instance
    profiles = plugin.profile_manager.list_profiles()
    assert len(profiles) == 9
    assert all(profile.built_in for profile in profiles)


def test_profile_categories_cover_the_requested_taxonomy() -> None:
    plugin = _get_nikto_plugin().instance
    categories = {profile.category for profile in plugin.profile_manager.list_profiles()}
    assert categories == set(ProfileCategory)


def test_default_profile_is_default_scan() -> None:
    from backend.plugins.plugins.nikto.plugin import DEFAULT_PROFILE_ID

    plugin = _get_nikto_plugin().instance
    assert plugin.profile_manager.get(DEFAULT_PROFILE_ID).id == "default_scan"


def test_search_filters_by_category_and_risk() -> None:
    plugin = _get_nikto_plugin().instance
    ssl_profiles = plugin.profile_manager.search(category=ProfileCategory.SSL)
    assert all(profile.category == ProfileCategory.SSL for profile in ssl_profiles)
    assert any(profile.id == "ssl_scan" for profile in ssl_profiles)

    low_risk = plugin.profile_manager.search(risk_level=RiskLevel.LOW)
    assert all(profile.risk_level == RiskLevel.LOW for profile in low_risk)


# -- Command builder -----------------------------------------------------------


def _profile(**overrides) -> ScanProfile:
    defaults = dict(
        id="test_profile", name="Test", description="d", category=ProfileCategory.DEFAULT,
        supported_targets=[TargetType.URL],
    )
    defaults.update(overrides)
    return ScanProfile(**defaults)


def test_command_builder_applies_tuning_plugins_and_timeout_from_profile() -> None:
    profile = _profile(tuning="1,2,3", plugins=["headers"], timeout_seconds=15)
    command = build_command(profile, "example.com", "nikto")
    assert command == ["nikto", "-h", "example.com", "-Tuning", "1,2,3", "-Plugins", "headers",
                        "-timeout", "15", "-Format", "xml", "-o", "-"]


def test_command_builder_advanced_options_override_profile() -> None:
    profile = _profile(tuning="1", plugins=["headers"])
    advanced = AdvancedOptions(tuning="8,9", additional_arguments=["-evasion", "1"])
    command = build_command(profile, "example.com", "nikto", advanced=advanced)
    assert "-Tuning" in command
    assert command[command.index("-Tuning") + 1] == "8,9"
    assert "-evasion" in command


def test_command_builder_applies_port_and_ssl_from_resolved_target() -> None:
    profile = _profile()
    command = build_command(profile, "example.com", "nikto", port="8443", use_ssl=True)
    assert "-p" in command and command[command.index("-p") + 1] == "8443"
    assert "-ssl" in command


def test_command_builder_always_ends_with_xml_output() -> None:
    profile = _profile()
    command = build_command(profile, "example.com", "nikto")
    assert command[-4:] == ["-Format", "xml", "-o", "-"]


def test_plugin_build_command_uses_default_profile_when_none_specified() -> None:
    plugin = _get_nikto_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.HOSTNAME, target_value="example.com", output_directory=Path("."), timeout_seconds=60
    )
    command = plugin.build_command(context)
    assert "-h" in command and "example.com" in command


def test_plugin_build_command_raises_for_unknown_profile() -> None:
    """Catches the framework's stable PluginNotFoundError, not this module's own ProfileNotFoundError
    import -- the plugin's directory is loaded as a synthetic package with its own fresh module
    identity (see backend/plugins/plugins/nmap/README.md's equivalent test for the full explanation),
    so an exception raised from inside it is not the same class object as this file's normal import."""
    plugin = _get_nikto_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.HOSTNAME, target_value="example.com", output_directory=Path("."),
        timeout_seconds=60, profile_id="does-not-exist",
    )
    with pytest.raises(FrameworkPluginNotFoundError):
        plugin.build_command(context)


# -- Target validation / resolution -------------------------------------------


@pytest.mark.parametrize(
    ("target_type", "target_value", "expected"),
    [
        (TargetType.URL, "https://example.com/path", True),
        (TargetType.HOSTNAME, "example.com", True),
        (TargetType.DOMAIN, "example.com", True),
        (TargetType.IPV4, "127.0.0.1", False),
        (TargetType.CIDR, "10.0.0.0/24", False),
    ],
)
def test_validate_target(target_type: TargetType, target_value: str, expected: bool) -> None:
    assert validate_nikto_target(target_type, target_value) is expected


def test_resolve_target_extracts_host_port_and_ssl_from_url() -> None:
    resolved = resolve_nikto_target(TargetType.URL, "https://example.com:8443/some/path")
    assert resolved.host == "example.com"
    assert resolved.port == "8443"
    assert resolved.use_ssl is True


def test_resolve_target_passes_through_hostname() -> None:
    resolved = resolve_nikto_target(TargetType.HOSTNAME, "example.com")
    assert resolved.host == "example.com"
    assert resolved.port is None
    assert resolved.use_ssl is False


# -- Parser ---------------------------------------------------------------------

_SAMPLE_XML = """<?xml version="1.0"?>
<niktoscan>
<scandetails targetip="93.184.216.34" targethostname="example.com" targetport="80">
<item id="999970" osvdbid="3268" method="GET">
<description>Apache/2.4.49 appears to be outdated, vulnerable to CVE-2021-41773 (path traversal, CWE-22)</description>
<uri>/icons/</uri>
<namelink>http://example.com/icons/</namelink>
<iplink>http://93.184.216.34/icons/</iplink>
</item>
</scandetails>
</niktoscan>"""


def test_parse_extracts_host_and_findings() -> None:
    raw = PluginRawOutput(stdout=_SAMPLE_XML, exit_code=0)
    result = parse_nikto_output(raw)
    assert result is not None
    assert len(result.hosts) == 1
    host = result.hosts[0]
    assert host.target_ip == "93.184.216.34"
    assert host.target_hostname == "example.com"
    assert len(host.findings) == 1
    assert host.findings[0].osvdb_id == "3268"


def test_parse_returns_none_for_malformed_xml() -> None:
    raw = PluginRawOutput(stdout="not xml at all <<<", exit_code=0)
    assert parse_nikto_output(raw) is None


def test_parse_handles_empty_stdout() -> None:
    raw = PluginRawOutput(stdout="", exit_code=1)
    assert parse_nikto_output(raw) is None


# -- Normalizer -------------------------------------------------------------------


def test_normalize_extracts_cve_and_cwe_from_finding_text() -> None:
    raw = PluginRawOutput(stdout=_SAMPLE_XML, exit_code=0)
    normalized = normalize_nikto_output(parse_nikto_output(raw))
    assert isinstance(normalized, NormalizedOutput)
    assert len(normalized.hosts) == 1
    assert normalized.hosts[0].hostname == "example.com"
    assert normalized.hosts[0].addresses[0].ip_address == "93.184.216.34"
    assert normalized.hosts[0].state == HostState.UP

    observation = normalized.observations[0]
    assert "CVE-2021-41773" in observation.detail
    assert "CWE-22" in observation.detail
    assert observation.category == "web"


def test_normalize_never_produces_a_title_split_on_a_version_number() -> None:
    """Real bug found during Phase 11: splitting a title on '.' truncated 'Apache/2.4.49...' to 'Apache/2'."""
    raw = PluginRawOutput(stdout=_SAMPLE_XML, exit_code=0)
    normalized = normalize_nikto_output(parse_nikto_output(raw))
    assert normalized.observations[0].title.startswith("Apache/2.4.49")


def test_normalize_handles_no_parsed_output() -> None:
    assert normalize_nikto_output(None) == NormalizedOutput()


def test_normalize_handles_host_with_no_findings() -> None:
    raw = PluginRawOutput(
        stdout='<niktoscan><scandetails targetip="1.2.3.4" targethostname="h" targetport="80"></scandetails></niktoscan>',
        exit_code=0,
    )
    normalized = normalize_nikto_output(parse_nikto_output(raw))
    assert len(normalized.hosts) == 1
    assert normalized.observations == []


# -- Custom profile CRUD --------------------------------------------------------


def test_custom_profile_crud_lifecycle(tmp_path: Path) -> None:
    manager = ProfileManager(Path(__file__).resolve().parent.parent / "plugins" / "plugins" / "nikto" / "profiles", tmp_path)
    created = manager.create_custom(
        {"id": "my_custom", "name": "Mine", "description": "d", "category": "custom", "supported_targets": ["url"]}
    )
    assert created.built_in is False

    updated = manager.update_custom("my_custom", {**created.model_dump(), "name": "Renamed"})
    assert updated.name == "Renamed"

    manager.delete_custom("my_custom")
    with pytest.raises(ProfileNotFoundError):
        manager.get("my_custom")


def test_built_in_profile_cannot_be_edited_or_deleted(tmp_path: Path) -> None:
    manager = ProfileManager(Path(__file__).resolve().parent.parent / "plugins" / "plugins" / "nikto" / "profiles", tmp_path)
    with pytest.raises(ProfileValidationError):
        manager.update_custom("default_scan", {"id": "default_scan", "name": "x", "description": "d",
                                                "category": "default", "supported_targets": ["url"]})
    with pytest.raises(ProfileValidationError):
        manager.delete_custom("default_scan")


def test_duplicate_id_rejected(tmp_path: Path) -> None:
    manager = ProfileManager(Path(__file__).resolve().parent.parent / "plugins" / "plugins" / "nikto" / "profiles", tmp_path)
    with pytest.raises(ProfileValidationError):
        manager.create_custom(
            {"id": "default_scan", "name": "x", "description": "d", "category": "custom", "supported_targets": ["url"]}
        )


# -- Real execution (skipped unless nikto is actually installed) ---------------


@pytest.mark.skipif(not NIKTO_INSTALLED, reason="nikto is not installed on this machine")
@pytest.mark.asyncio
async def test_real_execute_against_example_com_produces_real_output(tmp_path: Path) -> None:
    plugin = _get_nikto_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.HOSTNAME, target_value="example.com", output_directory=tmp_path,
        timeout_seconds=120, profile_id="headers",
    )
    plugin.prepare(context)
    command = plugin.build_command(context)
    raw_output = await plugin.execute(command, context)
    assert raw_output.exit_code == 0
    parsed = plugin.parse(raw_output)
    normalized = plugin.normalize(parsed)
    assert isinstance(normalized, NormalizedOutput)
