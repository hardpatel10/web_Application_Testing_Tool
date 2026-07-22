"""Tests for the SSLScan plugin: profiles, command generation, XML parsing, normalization.

Profile loading/validation, command generation, and XML parsing/normalization
are pure and fully host-agnostic (no real ``sslscan`` binary needed). The
real-execution test is skipped outright if ``sslscan`` isn't actually
installed on the machine running the tests -- the same host-agnostic
philosophy ``test_nuclei_plugin.py``/``test_nikto_plugin.py`` already use.

``_SAMPLE_XML`` is real ``sslscan 2.1.5`` output against ``example.com``,
not a hand-guessed fixture -- captured verbatim so the parser tests catch
a real field-name regression, not just whatever shape this module's own
author assumed.
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
from backend.plugins.plugins.sslscan.command_builder import build_command
from backend.plugins.plugins.sslscan.models import AdvancedOptions, ProfileCategory, RiskLevel, ScanProfile
from backend.plugins.plugins.sslscan.normalizer import normalize_sslscan_output
from backend.plugins.plugins.sslscan.parser import parse_sslscan_output
from backend.plugins.plugins.sslscan.profile_manager import ProfileManager, ProfileNotFoundError, ProfileValidationError
from backend.plugins.plugins.sslscan.validator import resolve_sslscan_target, validate_sslscan_target
from backend.plugins.sdk import PluginRawOutput

SSLSCAN_INSTALLED = shutil.which("sslscan") is not None


def _get_sslscan_plugin():
    manager = get_plugin_manager(get_settings().plugins_dir)
    manager.discover_and_register()
    return manager.get_plugin("sslscan")


# -- Built-in profile loading -------------------------------------------------


def test_all_built_in_profiles_load_and_validate() -> None:
    plugin = _get_sslscan_plugin().instance
    profiles = plugin.profile_manager.list_profiles()
    assert len(profiles) == 6
    assert all(profile.built_in for profile in profiles)


def test_profile_categories_cover_the_requested_taxonomy() -> None:
    plugin = _get_sslscan_plugin().instance
    categories = {profile.category for profile in plugin.profile_manager.list_profiles()}
    assert categories == set(ProfileCategory)


def test_default_profile_is_default_scan() -> None:
    from backend.plugins.plugins.sslscan.plugin import DEFAULT_PROFILE_ID

    plugin = _get_sslscan_plugin().instance
    profile = plugin.profile_manager.get(DEFAULT_PROFILE_ID)
    assert profile.id == "default_scan"


def test_search_filters_by_category_and_risk() -> None:
    plugin = _get_sslscan_plugin().instance
    cert_profiles = plugin.profile_manager.search(category=ProfileCategory.CERTIFICATE)
    assert all(profile.category == ProfileCategory.CERTIFICATE for profile in cert_profiles)
    assert any(profile.id == "certificate_analysis" for profile in cert_profiles)


# -- Target resolution ---------------------------------------------------------


@pytest.mark.parametrize(
    ("target_type", "target_value", "expected"),
    [
        (TargetType.URL, "https://example.com/path", True),
        (TargetType.HOSTNAME, "example.com", True),
        (TargetType.DOMAIN, "example.com", True),
        (TargetType.IPV4, "127.0.0.1", True),
        (TargetType.IPV6, "::1", True),
        (TargetType.CIDR, "10.0.0.0/24", False),
    ],
)
def test_validate_target(target_type: TargetType, target_value: str, expected: bool) -> None:
    assert validate_sslscan_target(target_type, target_value) is expected


def test_resolve_url_target_extracts_host_and_port() -> None:
    resolved = resolve_sslscan_target(TargetType.URL, "https://example.com:8443/path")
    assert resolved.host == "example.com"
    assert resolved.port == 8443
    assert resolved.ip_version is None


def test_resolve_url_target_without_explicit_port() -> None:
    resolved = resolve_sslscan_target(TargetType.URL, "https://example.com")
    assert resolved.host == "example.com"
    assert resolved.port is None


def test_resolve_ipv6_target_sets_ip_version() -> None:
    resolved = resolve_sslscan_target(TargetType.IPV6, "::1")
    assert resolved.host == "::1"
    assert resolved.ip_version == "6"


def test_resolve_hostname_target_passes_through() -> None:
    resolved = resolve_sslscan_target(TargetType.HOSTNAME, "example.com")
    assert resolved.host == "example.com"
    assert resolved.port is None
    assert resolved.ip_version is None


# -- Command builder -----------------------------------------------------------


def _profile(**overrides) -> ScanProfile:
    defaults = dict(
        id="test_profile", name="Test", description="d", category=ProfileCategory.DEFAULT,
        supported_targets=[TargetType.URL],
    )
    defaults.update(overrides)
    return ScanProfile(**defaults)


def test_command_builder_applies_fixed_profile_arguments() -> None:
    profile = _profile(arguments=["--show-certificate", "--ocsp"])
    command = build_command(profile, "example.com", "sslscan")
    assert command[0] == "sslscan"
    assert "--show-certificate" in command
    assert "--ocsp" in command


def test_command_builder_appends_port_to_host() -> None:
    profile = _profile()
    command = build_command(profile, "example.com", "sslscan", port=8443)
    assert command[-1] == "example.com:8443"


def test_command_builder_brackets_ipv6_host() -> None:
    profile = _profile()
    command = build_command(profile, "::1", "sslscan", ip_version="6")
    assert command[-1] == "[::1]"
    assert "--ipv6" in command


def test_command_builder_brackets_ipv6_host_with_port() -> None:
    profile = _profile()
    command = build_command(profile, "::1", "sslscan", port=443, ip_version="6")
    assert command[-1] == "[::1]:443"


def test_command_builder_advanced_options_override_profile() -> None:
    profile = _profile(timeout_seconds=3)
    advanced = AdvancedOptions(sni_name="vhost.example.com", timeout_seconds=10)
    command = build_command(profile, "example.com", "sslscan", advanced=advanced)
    assert "--sni-name=vhost.example.com" in command
    assert "--timeout=10" in command


def test_command_builder_falls_back_to_tool_default_timeout() -> None:
    profile = _profile()
    command = build_command(profile, "example.com", "sslscan", default_timeout=5)
    assert "--timeout=5" in command


def test_command_builder_always_ends_with_no_colour_and_xml_before_host() -> None:
    profile = _profile()
    command = build_command(profile, "example.com", "sslscan")
    assert command[-3:] == ["--no-colour", "--xml=-", "example.com"]


def test_plugin_build_command_uses_default_profile_when_none_specified() -> None:
    plugin = _get_sslscan_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.URL, target_value="https://example.com", output_directory=Path("."), timeout_seconds=60
    )
    command = plugin.build_command(context)
    assert command[-1] == "example.com"


def test_plugin_build_command_raises_for_unknown_profile() -> None:
    """Catches the framework's stable PluginNotFoundError, not this module's own ProfileNotFoundError
    import -- see backend/plugins/plugins/nmap/README.md's equivalent test for the full explanation
    of why the plugin's synthetically-loaded module identity makes the direct import not match."""
    plugin = _get_sslscan_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.URL, target_value="https://example.com", output_directory=Path("."),
        timeout_seconds=60, profile_id="does-not-exist",
    )
    with pytest.raises(FrameworkPluginNotFoundError):
        plugin.build_command(context)


# -- Parser (real sslscan 2.1.5 output against example.com) --------------------

_SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<document title="SSLScan Results" version="2.1.5" web="http://github.com/rbsec/sslscan">
 <ssltest host="example.com" sniname="example.com" port="443">
  <protocol type="ssl" version="2" enabled="0" />
  <protocol type="ssl" version="3" enabled="0" />
  <protocol type="tls" version="1.0" enabled="1" />
  <protocol type="tls" version="1.1" enabled="1" />
  <protocol type="tls" version="1.2" enabled="1" />
  <protocol type="tls" version="1.3" enabled="1" />
  <fallback supported="1" />
  <renegotiation supported="1" secure="1" />
  <compression supported="0" />
  <heartbleed sslversion="TLSv1.3" vulnerable="0" />
  <heartbleed sslversion="TLSv1.2" vulnerable="0" />
  <cipher status="preferred" sslversion="TLSv1.3" bits="128" cipher="TLS_AES_128_GCM_SHA256" id="0x1301" strength="strong" />
  <cipher status="accepted" sslversion="TLSv1.3" bits="256" cipher="TLS_AES_256_GCM_SHA384" id="0x1302" strength="strong" />
  <cipher status="preferred" sslversion="TLSv1.0" bits="128" cipher="ECDHE-RSA-AES128-SHA" id="0xC013" strength="acceptable" curve="25519" ecdhebits="253" />
  <cipher status="accepted" sslversion="TLSv1.0" bits="112" cipher="TLS_RSA_WITH_3DES_EDE_CBC_SHA" id="0x000A" strength="medium" />
  <group sslversion="TLSv1.3" bits="128" name="x25519" id="0x001d" />
 <certificates>
  <certificate type="short">
   <signature-algorithm>ecdsa-with-SHA256</signature-algorithm>
   <pk error="false" type="EC" curve_name="prime256v1" bits="128" />
   <subject><![CDATA[example.com]]></subject>
   <altnames><![CDATA[DNS:example.com, DNS:*.example.com]]></altnames>
   <issuer><![CDATA[Cloudflare TLS Issuing ECC CA 3]]></issuer>
   <self-signed>false</self-signed>
   <not-valid-before>May 31 21:39:12 2026 GMT</not-valid-before>
   <not-yet-valid>false</not-yet-valid>
   <not-valid-after>Aug 29 21:41:26 2026 GMT</not-valid-after>
   <expired>false</expired>
  </certificate>
 </certificates>
 </ssltest>
</document>
"""


def test_parse_extracts_protocols_ciphers_and_certificate() -> None:
    raw = PluginRawOutput(stdout=_SAMPLE_XML, exit_code=0)
    result = parse_sslscan_output(raw)
    assert result is not None
    assert len(result.hosts) == 1
    host = result.hosts[0]
    assert host.host == "example.com"
    assert host.sni_name == "example.com"
    assert host.port == 443

    enabled = [p for p in host.protocols if p.enabled]
    assert {(p.protocol_type, p.version) for p in enabled} == {("tls", "1.0"), ("tls", "1.1"), ("tls", "1.2"), ("tls", "1.3")}
    disabled = [p for p in host.protocols if not p.enabled]
    assert {(p.protocol_type, p.version) for p in disabled} == {("ssl", "2"), ("ssl", "3")}

    assert host.fallback_supported is True
    assert host.renegotiation_supported is True
    assert host.renegotiation_secure is True
    assert host.compression_supported is False
    assert host.heartbleed == {"TLSv1.3": False, "TLSv1.2": False}

    assert len(host.ciphers) == 4
    weak_cipher = next(c for c in host.ciphers if c.cipher == "TLS_RSA_WITH_3DES_EDE_CBC_SHA")
    assert weak_cipher.strength == "medium"
    assert weak_cipher.ssl_version == "TLSv1.0"

    assert len(host.groups) == 1
    assert host.groups[0].name == "x25519"

    assert len(host.certificates) == 1
    cert = host.certificates[0]
    assert cert.subject == "example.com"
    assert cert.issuer == "Cloudflare TLS Issuing ECC CA 3"
    assert cert.self_signed is False
    assert cert.expired is False
    assert cert.pk_type == "EC"
    assert cert.pk_bits == 128


def test_parse_handles_empty_stdout() -> None:
    raw = PluginRawOutput(stdout="", exit_code=0)
    assert parse_sslscan_output(raw) is None


def test_parse_handles_no_templates_error_output() -> None:
    """A connection failure or malformed run produces no <ssltest> element -- parse returns None,
    never a fabricated empty-but-present host."""
    raw = PluginRawOutput(stdout='<?xml version="1.0"?><document></document>', exit_code=1)
    assert parse_sslscan_output(raw) is None


# -- Normalizer ------------------------------------------------------------------


def test_normalize_produces_host_and_two_observation_sources() -> None:
    raw = PluginRawOutput(stdout=_SAMPLE_XML, exit_code=0)
    normalized = normalize_sslscan_output(parse_sslscan_output(raw))
    assert isinstance(normalized, NormalizedOutput)
    assert len(normalized.hosts) == 1
    assert normalized.hosts[0].hostname == "example.com"
    assert normalized.hosts[0].state == HostState.UP

    sources = {o.source for o in normalized.observations}
    assert sources == {"sslscan-enum-ciphers", "sslscan-cert"}


def test_normalize_protocol_detail_only_names_enabled_protocols() -> None:
    """Regression guard: printing a disabled legacy protocol's name (e.g. "SSLv2: disabled")
    would make backend.correlation.rules.tls_rules.WeakTlsProtocolOrCipherRule's plain substring
    match false-positive on a protocol that is explicitly NOT present."""
    raw = PluginRawOutput(stdout=_SAMPLE_XML, exit_code=0)
    normalized = normalize_sslscan_output(parse_sslscan_output(raw))
    protocol_observation = next(o for o in normalized.observations if o.source == "sslscan-enum-ciphers")
    assert "sslv2" not in protocol_observation.detail.lower()
    assert "sslv3" not in protocol_observation.detail.lower()
    assert "tlsv1.0" in protocol_observation.detail.lower()


def test_normalize_certificate_detail_omits_false_facts() -> None:
    """Regression guard: a non-expired, non-self-signed certificate's detail text must never
    contain the words "expired"/"self-signed" at all -- not even in a negated ("not expired")
    form -- since the Correlation Engine's match is a plain substring search with no negation
    awareness."""
    raw = PluginRawOutput(stdout=_SAMPLE_XML, exit_code=0)
    normalized = normalize_sslscan_output(parse_sslscan_output(raw))
    cert_observation = next(o for o in normalized.observations if o.source == "sslscan-cert")
    assert "expired" not in cert_observation.detail.lower()
    assert "self-signed" not in cert_observation.detail.lower()
    assert "self signed" not in cert_observation.detail.lower()


def test_normalize_certificate_detail_states_expired_and_self_signed_when_true() -> None:
    xml = _SAMPLE_XML.replace("<self-signed>false</self-signed>", "<self-signed>true</self-signed>").replace(
        "<expired>false</expired>", "<expired>true</expired>"
    )
    raw = PluginRawOutput(stdout=xml, exit_code=0)
    normalized = normalize_sslscan_output(parse_sslscan_output(raw))
    cert_observation = next(o for o in normalized.observations if o.source == "sslscan-cert")
    assert "self-signed" in cert_observation.detail.lower()
    assert "expired" in cert_observation.detail.lower()


def test_normalize_handles_no_parsed_output() -> None:
    assert normalize_sslscan_output(None) == NormalizedOutput()


def test_normalize_never_fabricates_a_finding_only_observations() -> None:
    raw = PluginRawOutput(stdout=_SAMPLE_XML, exit_code=0)
    normalized = normalize_sslscan_output(parse_sslscan_output(raw))
    for observation in normalized.observations:
        assert not hasattr(observation, "severity")
        assert not hasattr(observation, "cvss_score")


# -- Custom profile CRUD --------------------------------------------------------


def test_custom_profile_crud_lifecycle(tmp_path: Path) -> None:
    manager = ProfileManager(Path(__file__).resolve().parent.parent / "plugins" / "plugins" / "sslscan" / "profiles", tmp_path)
    created = manager.create_custom(
        {"id": "my_custom", "name": "Mine", "description": "d", "category": "custom", "supported_targets": ["hostname"]}
    )
    assert created.built_in is False
    manager.delete_custom("my_custom")
    with pytest.raises(ProfileNotFoundError):
        manager.get("my_custom")


def test_built_in_profile_cannot_be_edited_or_deleted(tmp_path: Path) -> None:
    manager = ProfileManager(Path(__file__).resolve().parent.parent / "plugins" / "plugins" / "sslscan" / "profiles", tmp_path)
    with pytest.raises(ProfileValidationError):
        manager.delete_custom("default_scan")


# -- Real execution (skipped unless sslscan is actually installed) -------------


@pytest.mark.skipif(not SSLSCAN_INSTALLED, reason="sslscan is not installed on this machine")
@pytest.mark.asyncio
async def test_real_execute_against_example_com_produces_real_output(tmp_path: Path) -> None:
    plugin = _get_sslscan_plugin().instance
    context = PluginExecutionContext(
        target_type=TargetType.URL, target_value="https://example.com", output_directory=tmp_path, timeout_seconds=60,
    )
    plugin.prepare(context)
    command = plugin.build_command(context)
    raw_output = await plugin.execute(command, context)
    parsed = plugin.parse(raw_output)
    normalized = plugin.normalize(parsed)
    assert isinstance(normalized, NormalizedOutput)
    assert len(normalized.hosts) == 1
