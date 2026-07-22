"""Tests for the Nmap plugin: profiles, command generation, XML parsing, normalization.

Profile loading/validation/search, command generation, and XML parsing/
normalization are pure and fully host-agnostic (no real ``nmap`` binary
needed). A handful of tests exercise a real scan against 127.0.0.1/localhost
and are skipped outright if ``nmap`` isn't actually installed on the
machine running the tests -- the same host-agnostic philosophy already
used for Tool Management (``test_tools.py``).
"""

import shutil
from pathlib import Path

import pytest

from backend.core.config import get_settings
from backend.models.enums import HostState, NetworkProtocol, PortState, TargetType
from backend.plugins.exceptions import PluginNotFoundError as FrameworkPluginNotFoundError
from backend.plugins.manager.plugin_manager import get_plugin_manager
from backend.plugins.models.execution import PluginExecutionContext
from backend.plugins.models.normalized import NormalizedOutput
from backend.plugins.plugins.nmap.command_builder import build_command
from backend.plugins.plugins.nmap.models import AdvancedOptions, ProfileCategory, RiskLevel, ScanProfile
from backend.plugins.plugins.nmap.normalizer import normalize_nmap_output
from backend.plugins.plugins.nmap.parser import NmapHost, NmapOsMatch, NmapScanResult, NmapScript, parse_nmap_output
from backend.plugins.plugins.nmap.profile_manager import ProfileManager, ProfileNotFoundError, ProfileValidationError
from backend.plugins.plugins.nmap.validator import resolve_nmap_target, validate_nmap_target
from backend.plugins.sdk import PluginRawOutput

NMAP_INSTALLED = shutil.which("nmap") is not None


def _get_nmap_plugin():
    manager = get_plugin_manager(get_settings().plugins_dir)
    manager.discover_and_register()
    return manager.get_plugin("nmap")


# -- Built-in profile loading -------------------------------------------------


def test_all_built_in_profiles_load_and_validate() -> None:
    plugin = _get_nmap_plugin().instance
    profiles = plugin.profile_manager.list_profiles()

    assert len(profiles) >= 30
    assert all(profile.built_in for profile in profiles)
    assert len({profile.id for profile in profiles}) == len(profiles), "duplicate profile ids"
    for profile in profiles:
        assert profile.supported_targets
        assert profile.category in ProfileCategory
        assert profile.risk_level in RiskLevel


def test_profile_categories_cover_the_requested_taxonomy() -> None:
    plugin = _get_nmap_plugin().instance
    categories = {profile.category for profile in plugin.profile_manager.list_profiles()}
    expected = {
        ProfileCategory.TCP, ProfileCategory.UDP, ProfileCategory.SSL_TLS, ProfileCategory.SSH,
        ProfileCategory.SMB, ProfileCategory.SNMP, ProfileCategory.RDP, ProfileCategory.DNS,
        ProfileCategory.DATABASE, ProfileCategory.REMOTE_ACCESS, ProfileCategory.GENERAL_ENUMERATION,
        ProfileCategory.NETWORK_DISCOVERY,
    }
    assert expected.issubset(categories)


def test_search_filters_by_category_risk_and_query() -> None:
    profile_manager = _get_nmap_plugin().instance.profile_manager

    ssl_profiles = profile_manager.search(category=ProfileCategory.SSL_TLS)
    assert ssl_profiles and all(profile.category == ProfileCategory.SSL_TLS for profile in ssl_profiles)

    high_risk = profile_manager.search(risk_level=RiskLevel.HIGH)
    assert high_risk and all(profile.risk_level == RiskLevel.HIGH for profile in high_risk)

    heartbleed_results = profile_manager.search(query="heartbleed")
    assert any(profile.id == "heartbleed" for profile in heartbleed_results)


# -- Command generation: no hardcoded strings, purely data-driven -------------


def test_command_builder_is_driven_entirely_by_profile_data() -> None:
    """Two profiles differing only in their data produce correspondingly different commands."""
    base_kwargs = dict(
        id="profile_a", name="A", description="A", category=ProfileCategory.TCP, supported_targets=[TargetType.IPV4],
    )
    profile_a = ScanProfile(**base_kwargs, arguments=["-sS"], required_ports="80")
    profile_b = ScanProfile(**{**base_kwargs, "id": "profile_b"}, arguments=["-sU"], required_ports="53")

    command_a = build_command(profile_a, "10.0.0.1", "nmap")
    command_b = build_command(profile_b, "10.0.0.1", "nmap")

    assert command_a == ["nmap", "-sS", "-p", "80", "-oX", "-", "10.0.0.1"]
    assert command_b == ["nmap", "-sU", "-p", "53", "-oX", "-", "10.0.0.1"]
    assert command_a != command_b


def test_advanced_options_override_profile_defaults() -> None:
    profile = ScanProfile(
        id="p", name="P", description="P", category=ProfileCategory.TCP, supported_targets=[TargetType.IPV4],
        arguments=["-sV"], required_ports="1-1000", required_scripts=["http-headers"], script_args={"a": "1"},
    )
    advanced = AdvancedOptions(timing=4, retries=2, port_range="443", verbosity=2, script_args={"b": "2"}, additional_arguments=["--reason"])

    command = build_command(profile, "example.com", "nmap", advanced=advanced, default_retries=9, default_rate_limit=100)

    assert command == [
        "nmap", "-sV", "-T4", "--max-retries", "2", "--min-rate", "100",
        "-p", "443",  # advanced.port_range overrides profile.required_ports
        "--script", "http-headers",
        "--script-args", "a=1,b=2",
        "-vv", "--reason", "-oX", "-", "example.com",
    ]


def test_top_ports_used_when_no_explicit_port_range_given() -> None:
    profile = ScanProfile(
        id="p", name="P", description="P", category=ProfileCategory.UDP, supported_targets=[TargetType.IPV4], required_ports="161",
    )
    command = build_command(profile, "10.0.0.1", "nmap", advanced=AdvancedOptions(top_ports=20))
    assert "--top-ports" in command and "20" in command
    assert "-p" not in command  # top_ports takes priority over the profile's own required_ports


def test_default_retries_only_applied_when_advanced_does_not_override() -> None:
    profile = ScanProfile(id="p", name="P", description="P", category=ProfileCategory.TCP, supported_targets=[TargetType.IPV4])
    command_with_override = build_command(profile, "x", "nmap", advanced=AdvancedOptions(retries=5), default_retries=1)
    command_without_override = build_command(profile, "x", "nmap", default_retries=1)
    assert command_with_override.count("--max-retries") == 1
    assert command_with_override[command_with_override.index("--max-retries") + 1] == "5"
    assert command_without_override[command_without_override.index("--max-retries") + 1] == "1"


def test_build_command_always_ends_with_xml_output_and_target() -> None:
    profile = ScanProfile(id="p", name="P", description="P", category=ProfileCategory.TCP, supported_targets=[TargetType.IPV4])
    command = build_command(profile, "192.0.2.1", "nmap")
    assert command[-3:] == ["-oX", "-", "192.0.2.1"]


# -- Plugin-level build_command() (profile lookup + defaults) -----------------


def test_plugin_build_command_uses_default_profile_when_none_specified() -> None:
    plugin = _get_nmap_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.IPV4, target_value="127.0.0.1", output_directory=Path("."), timeout_seconds=60,
    )
    command = plugin.build_command(context)
    assert "-sS" in command and "-sV" in command and "-O" in command and "-sC" in command  # intelligent_standard, the documented default


def test_plugin_build_command_uses_named_profile() -> None:
    plugin = _get_nmap_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.IPV4, target_value="127.0.0.1", output_directory=Path("."), timeout_seconds=60,
        profile_id="tcp_full",
    )
    command = plugin.build_command(context)
    assert "-sS" in command
    assert "1-65535" in command


def test_plugin_build_command_raises_for_unknown_profile() -> None:
    """Goes through the real, registered (synthetically-loaded, see the Phase 4 loader) plugin instance.

    Catches the plugin framework's stable ``PluginNotFoundError`` --
    imported here via ``backend.plugins.exceptions``, the same ordinary
    way everywhere -- rather than this module's own ``ProfileNotFoundError``
    import. The two are *not* interchangeable: this plugin's directory is
    loaded as a synthetic package with its own fresh module identity, so
    the ``ProfileNotFoundError`` this test file imports is a different
    class object than the one actually raised from inside that synthetic
    module, even though both are named identically and both inherit from
    the same stable ``PluginNotFoundError`` -- confirmed by first writing
    this assertion against the plugin-local class and watching it fail
    with the real exception escaping uncaught, not a clean assertion
    failure. See ``backend.services.scan_profile_service``'s docstring for
    the full explanation; this test exists so a future refactor can't
    silently reintroduce the mismatch without a test noticing.
    """
    plugin = _get_nmap_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.IPV4, target_value="127.0.0.1", output_directory=Path("."), timeout_seconds=60,
        profile_id="not-a-real-profile",
    )
    with pytest.raises(FrameworkPluginNotFoundError):
        plugin.build_command(context)


# -- Target validation ---------------------------------------------------------


@pytest.mark.parametrize(
    ("target_type", "target_value", "expected"),
    [
        (TargetType.IPV4, "127.0.0.1", True),
        (TargetType.HOSTNAME, "localhost", True),
        (TargetType.HOSTNAME, "scanme.nmap.org", True),
        (TargetType.IPV4, "10.0.0.5", True),  # private IP -- Nmap can target it, this platform doesn't restrict it
        (TargetType.CIDR, "192.168.1.0/24", True),
        (TargetType.DOMAIN, "example.com", True),
        (TargetType.URL, "https://example.com/path", True),  # reduced to its host, see resolve_nmap_target
        (TargetType.URL, "not-a-url", False),
    ],
)
def test_validate_target(target_type: TargetType, target_value: str, expected: bool) -> None:
    assert validate_nmap_target(target_type, target_value) is expected


def test_validate_target_rejects_malformed_values() -> None:
    assert validate_nmap_target(TargetType.IPV4, "not-an-ip") is False


@pytest.mark.parametrize(
    ("target_type", "target_value", "expected_host"),
    [
        (TargetType.URL, "https://example.com/", "example.com"),
        (TargetType.URL, "https://example.com", "example.com"),
        (TargetType.URL, "http://scanme.nmap.org/some/path?x=1", "scanme.nmap.org"),
        (TargetType.URL, "https://Example.COM:8443/", "example.com"),
        (TargetType.IPV4, "192.168.1.20", "192.168.1.20"),
        (TargetType.HOSTNAME, "scanme.nmap.org", "scanme.nmap.org"),
    ],
)
def test_resolve_nmap_target(target_type: TargetType, target_value: str, expected_host: str) -> None:
    assert resolve_nmap_target(target_type, target_value) == expected_host


def test_plugin_build_command_reduces_url_target_to_bare_host() -> None:
    plugin = _get_nmap_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.URL, target_value="https://example.com/", output_directory=Path("."), timeout_seconds=60,
    )
    command = plugin.build_command(context)
    assert command[-1] == "example.com"


# -- XML parsing ----------------------------------------------------------------

_SAMPLE_NMAP_XML = """<?xml version="1.0"?>
<nmaprun scanner="nmap">
  <host>
    <status state="up"/>
    <address addr="192.0.2.10" addrtype="ipv4"/>
    <address addr="AA:BB:CC:DD:EE:FF" addrtype="mac" vendor="Example Vendor"/>
    <hostnames><hostname name="host.example.com" type="user"/></hostnames>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="8.9" extrainfo="Ubuntu"/>
        <script id="ssh2-enum-algos" output="kex_algorithms: (3)&#10;  curve25519-sha256"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="closed"/>
        <service name="http"/>
      </port>
    </ports>
    <os>
      <osmatch name="Linux 5.X" accuracy="93"/>
      <osmatch name="Linux 4.X" accuracy="88"/>
    </os>
    <hostscript>
      <script id="smb-os-discovery" output="OS: Linux"/>
    </hostscript>
  </host>
</nmaprun>
"""


def test_parse_extracts_hosts_addresses_ports_services_os_and_scripts() -> None:
    raw = PluginRawOutput(stdout=_SAMPLE_NMAP_XML, exit_code=0)
    result = parse_nmap_output(raw)

    assert result is not None
    assert len(result.hosts) == 1
    host = result.hosts[0]
    assert host.status == "up"
    assert ("192.0.2.10", "ipv4") in host.addresses
    assert ("AA:BB:CC:DD:EE:FF", "mac") in host.addresses
    assert host.mac_vendor == "Example Vendor"
    assert host.hostnames == ["host.example.com"]
    assert host.os_matches == [NmapOsMatch(name="Linux 5.X", accuracy=93), NmapOsMatch(name="Linux 4.X", accuracy=88)]
    assert len(host.ports) == 2

    ssh_port = next(p for p in host.ports if p.port == 22)
    assert ssh_port.protocol == "tcp"
    assert ssh_port.state == "open"
    assert ssh_port.service_name == "ssh"
    assert ssh_port.product == "OpenSSH"
    assert ssh_port.version == "8.9"
    assert ssh_port.extra_info == "Ubuntu"
    assert ssh_port.scripts == [NmapScript(script_id="ssh2-enum-algos", output="kex_algorithms: (3)\n  curve25519-sha256")]

    http_port = next(p for p in host.ports if p.port == 80)
    assert http_port.state == "closed"

    assert host.host_scripts == [NmapScript(script_id="smb-os-discovery", output="OS: Linux")]


def test_parse_returns_none_for_malformed_xml() -> None:
    raw = PluginRawOutput(stdout="<not valid xml", exit_code=1)
    assert parse_nmap_output(raw) is None


def test_parse_handles_empty_stdout() -> None:
    raw = PluginRawOutput(stdout="", exit_code=1)
    assert parse_nmap_output(raw) is None


# -- Normalization: hosts/services/observations, never a finding/CVSS -------


def test_normalize_produces_hosts_services_and_observations() -> None:
    raw = PluginRawOutput(stdout=_SAMPLE_NMAP_XML, exit_code=0)
    parsed = parse_nmap_output(raw)
    normalized = normalize_nmap_output(parsed)

    assert isinstance(normalized, NormalizedOutput)
    assert len(normalized.hosts) == 1
    host = normalized.hosts[0]
    assert [a.ip_address for a in host.addresses] == ["192.0.2.10"]
    assert host.mac_address == "AA:BB:CC:DD:EE:FF"
    assert host.mac_vendor == "Example Vendor"
    assert host.hostname == "host.example.com"
    assert host.state == HostState.UP
    # Every OS candidate is kept (not just the highest-accuracy one) -- Phase 8
    # fixed the prior data loss where all but the best match were discarded.
    best_os = max(host.os_matches, key=lambda match: match.accuracy)
    assert best_os.name == "Linux 5.X"
    assert best_os.accuracy == 93

    assert len(host.services) == 2
    ssh_service = next(s for s in host.services if s.port == 22)
    assert ssh_service.protocol == NetworkProtocol.TCP
    assert ssh_service.state == PortState.OPEN
    assert ssh_service.product == "OpenSSH"

    # One host script + one port script observation, correctly associated back to the one host.
    assert len(normalized.observations) == 2
    sources = {observation.source for observation in normalized.observations}
    assert sources == {"smb-os-discovery", "ssh2-enum-algos"}
    for observation in normalized.observations:
        assert observation.host_index == 0
        # Structural guarantee, not just absence-of-data: this model has no field to hold a
        # severity or CVSS score at all -- per CLAUDE.md, normalization never judges a finding.
        assert not hasattr(observation, "severity")
        assert not hasattr(observation, "cvss_score")


def test_normalize_handles_no_parsed_output() -> None:
    normalized = normalize_nmap_output(None)
    assert normalized == NormalizedOutput(hosts=[], observations=[])


def test_down_host_state_maps_correctly() -> None:
    result = NmapScanResult(hosts=[NmapHost(status="down", addresses=[("192.0.2.99", "ipv4")])])
    normalized = normalize_nmap_output(result)
    assert normalized.hosts[0].state == HostState.DOWN


# -- Custom profile CRUD (isolated tmp_path, never touches the real profiles dir) --


def test_custom_profile_crud_lifecycle(tmp_path: Path) -> None:
    built_in_dir = tmp_path / "built_in"
    built_in_dir.mkdir()
    custom_dir = tmp_path / "custom"
    manager = ProfileManager(built_in_dir, custom_dir)

    created = manager.create_custom(
        {
            "id": "custom_one", "name": "Custom One", "description": "d", "category": "tcp",
            "supported_targets": ["ipv4"], "arguments": ["-sT"],
        }
    )
    assert created.built_in is False
    assert manager.get("custom_one").name == "Custom One"

    updated = manager.update_custom(
        "custom_one",
        {"id": "custom_one", "name": "Renamed", "description": "d2", "category": "tcp", "supported_targets": ["ipv4"]},
    )
    assert updated.name == "Renamed"

    duplicate = manager.duplicate("custom_one", "custom_two")
    assert duplicate.id == "custom_two"
    assert {p.id for p in manager.list_profiles()} == {"custom_one", "custom_two"}

    exported = manager.export_profile("custom_two")
    assert exported["id"] == "custom_two"
    assert "built_in" not in exported

    manager.delete_custom("custom_one")
    manager.delete_custom("custom_two")
    assert manager.list_profiles() == []


def test_custom_profile_duplicate_id_rejected(tmp_path: Path) -> None:
    manager = ProfileManager(tmp_path / "built_in", tmp_path / "custom")
    manager._built_in_dir.mkdir()
    payload = {"id": "dup", "name": "N", "description": "d", "category": "tcp", "supported_targets": ["ipv4"]}
    manager.create_custom(payload)
    with pytest.raises(ProfileValidationError):
        manager.create_custom(payload)


def test_built_in_profile_cannot_be_edited_or_deleted(tmp_path: Path) -> None:
    built_in_dir = tmp_path / "built_in"
    built_in_dir.mkdir()
    (built_in_dir / "fixed.json").write_text(
        '{"id": "fixed", "name": "Fixed", "description": "d", "category": "tcp", "supported_targets": ["ipv4"]}'
    )
    manager = ProfileManager(built_in_dir, tmp_path / "custom")

    with pytest.raises(ProfileValidationError):
        manager.update_custom("fixed", {"id": "fixed", "name": "x", "description": "d", "category": "tcp", "supported_targets": ["ipv4"]})
    with pytest.raises(ProfileValidationError):
        manager.delete_custom("fixed")


def test_unknown_profile_raises_not_found(tmp_path: Path) -> None:
    manager = ProfileManager(tmp_path / "built_in", tmp_path / "custom")
    manager._built_in_dir.mkdir()
    with pytest.raises(ProfileNotFoundError):
        manager.get("does-not-exist")


def test_invalid_profile_data_rejected(tmp_path: Path) -> None:
    manager = ProfileManager(tmp_path / "built_in", tmp_path / "custom")
    manager._built_in_dir.mkdir()
    with pytest.raises(ProfileValidationError):
        manager.create_custom({"id": "Bad-ID!", "name": "N", "description": "d", "category": "tcp", "supported_targets": ["ipv4"]})


def test_a_malformed_profile_file_is_skipped_not_crashed_on(tmp_path: Path) -> None:
    built_in_dir = tmp_path / "built_in"
    built_in_dir.mkdir()
    (built_in_dir / "broken.json").write_text("{not valid json")
    (built_in_dir / "invalid_schema.json").write_text('{"id": "x"}')  # missing required fields
    manager = ProfileManager(built_in_dir, tmp_path / "custom")
    assert manager.list_profiles() == []  # both skipped, no exception


# -- Real execution against a live nmap binary (skipped if not installed) -----


@pytest.mark.skipif(not NMAP_INSTALLED, reason="nmap is not installed on this machine")
async def test_real_execute_against_localhost_produces_real_output(tmp_path: Path) -> None:
    plugin = _get_nmap_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.IPV4, target_value="127.0.0.1", output_directory=tmp_path,
        timeout_seconds=60, profile_id="service_detection",
    )
    plugin.prepare(context)
    command = plugin.build_command(context)
    raw_output = await plugin.execute(command, context)

    assert raw_output.exit_code == 0
    assert raw_output.output_format.value == "xml"
    assert "<nmaprun" in raw_output.stdout

    parsed = plugin.parse(raw_output)
    assert parsed is not None
    assert len(parsed.hosts) == 1
    assert parsed.hosts[0].status == "up"

    normalized = plugin.normalize(parsed)
    assert isinstance(normalized, NormalizedOutput)
    assert len(normalized.hosts) == 1
    assert [a.ip_address for a in normalized.hosts[0].addresses] == ["127.0.0.1"]
