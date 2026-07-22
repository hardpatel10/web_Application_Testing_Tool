"""Normalizes parsed SSLScan output into the platform's common shape.

Produces hosts and observations only -- per ``.claude/CLAUDE.md``, this
never judges a protocol/cipher/certificate result, never assigns a
severity, and never fabricates a Finding. Every fact folded into an
observation's ``detail`` is exactly what SSLScan itself reported (a
protocol's own enabled/disabled flag, a cipher's own ``strength`` rating,
a certificate's own self-signed/expired/not-yet-valid flags) -- this
module only formats and groups those real facts, never adds a judgment
SSLScan didn't itself make.

Two observations per scanned host, deliberately mirroring the two NSE
scripts ``nmap/normalizer.py`` already produces observations for
(``ssl-enum-ciphers``, ``ssl-cert``): ``source="sslscan-enum-ciphers"``
(protocols/ciphers/groups/Heartbleed/etc.) and ``source="sslscan-cert"``
(one per certificate). ``backend/correlation/rules/tls_rules.py`` accepts
both the ``ssl-*`` (Nmap) and ``sslscan-*`` (this plugin) source labels,
so the same self-signed/expired/weak-protocol rules correlate evidence
from either or both tools into one Finding, without a second set of rules.

Text formatting is deliberately conservative about *when* a weak
protocol/cipher/certificate fact's own name or trigger word appears in
``detail``: only when SSLScan actually reported it as enabled/accepted/
true. ``tls_rules.py``'s matching is a plain case-insensitive substring
search over the whole ``detail`` string -- printing e.g. "SSLv2: disabled"
or "Expired: no" would make that plain substring search false-positive on
a fact that is explicitly *not* present. Every conditional fact below is
therefore only ever appended to ``detail`` when true, never stated in the
negative.
"""

from backend.models.enums import HostState, ObservationCategory, TargetType
from backend.plugins.models.normalized import NormalizedAddress, NormalizedHost, NormalizedObservation, NormalizedOutput

from .parser import SslCertificate, SslCipher, SslscanHost, SslscanScanResult

_PROTOCOL_LABELS: dict[tuple[str, str], str] = {
    ("ssl", "2"): "SSLv2",
    ("ssl", "3"): "SSLv3",
    ("tls", "1.0"): "TLSv1.0",
    ("tls", "1.1"): "TLSv1.1",
    ("tls", "1.2"): "TLSv1.2",
    ("tls", "1.3"): "TLSv1.3",
}

_IPV4_DIGITS_AND_DOTS = set("0123456789.")


def _protocol_label(protocol_type: str, version: str) -> str:
    return _PROTOCOL_LABELS.get((protocol_type, version), f"{protocol_type.upper()}v{version}")


def _is_ipv4_literal(value: str) -> bool:
    return bool(value) and value.count(".") == 3 and all(c in _IPV4_DIGITS_AND_DOTS for c in value)


def normalize_sslscan_output(parsed_output: SslscanScanResult | None) -> NormalizedOutput:
    if parsed_output is None:
        return NormalizedOutput()

    hosts: list[NormalizedHost] = []
    observations: list[NormalizedObservation] = []

    for index, host in enumerate(parsed_output.hosts):
        hosts.append(_normalize_host(host))
        observations.extend(_normalize_observations(host, host_index=index))

    return NormalizedOutput(hosts=hosts, observations=observations)


def _normalize_host(host: SslscanHost) -> NormalizedHost:
    is_ip = _is_ipv4_literal(host.host)
    return NormalizedHost(
        hostname=None if is_ip else host.host,
        fqdn=None if is_ip else host.host,
        addresses=[NormalizedAddress(ip_address=host.host, version=TargetType.IPV4)] if is_ip else [],
        # SSLScan only ever connects to the one target it was pointed at -- it never itself
        # reports host reachability the way an nmap ping/port scan does, so "SSLScan got a
        # <ssltest> result back at all" is the only honest reachability fact available here.
        state=HostState.UP if host.host else HostState.UNKNOWN,
    )


def _cipher_label(cipher: SslCipher) -> str:
    label = f"{cipher.cipher} ({cipher.bits} bit"
    if cipher.strength:
        label += f", {cipher.strength}"
    if cipher.curve:
        label += f", curve {cipher.curve}"
    return label + ")"


def _protocols_and_ciphers_detail(host: SslscanHost) -> str:
    enabled = [p for p in host.protocols if p.enabled]
    lines = [
        "Protocols enabled: " + (", ".join(_protocol_label(p.protocol_type, p.version) for p in enabled) if enabled else "none"),
        f"Protocol versions checked: {len(host.protocols)}, enabled: {len(enabled)}, disabled: {len(host.protocols) - len(enabled)}",
    ]

    if host.fallback_supported is not None:
        lines.append(f"TLS Fallback SCSV: {'supported' if host.fallback_supported else 'not supported'}")
    if host.renegotiation_supported is not None:
        detail = "supported" if host.renegotiation_supported else "not supported"
        if host.renegotiation_supported:
            detail += " (secure)" if host.renegotiation_secure else " (insecure)"
        lines.append(f"Secure Renegotiation: {detail}")
    if host.compression_supported is not None:
        lines.append(f"TLS Compression (CRIME): {'supported' if host.compression_supported else 'not supported'}")
    if host.heartbleed:
        vulnerable = sorted(version for version, is_vulnerable in host.heartbleed.items() if is_vulnerable)
        if vulnerable:
            lines.append(f"Heartbleed (CVE-2014-0160): vulnerable on {', '.join(vulnerable)}")
        else:
            lines.append(f"Heartbleed (CVE-2014-0160): not vulnerable ({len(host.heartbleed)} protocol version(s) checked)")

    preferred = [c for c in host.ciphers if c.status == "preferred"]
    if preferred:
        lines.append("")
        lines.append("Preferred cipher by protocol version:")
        lines.extend(f"  {cipher.ssl_version}: {_cipher_label(cipher)}" for cipher in preferred)

    accepted = [c for c in host.ciphers if c.status != "rejected"]
    if accepted:
        lines.append("")
        lines.append(f"Accepted cipher suites ({len(accepted)}):")
        lines.extend(f"  {cipher.ssl_version}  {_cipher_label(cipher)}" for cipher in accepted)

    if host.groups:
        lines.append("")
        lines.append("Key exchange groups offered:")
        lines.extend(f"  {group.ssl_version}: {group.name} ({group.bits} bit)" for group in host.groups)

    return "\n".join(lines)


def _certificate_detail(cert: SslCertificate) -> str:
    lines = [f"Subject: {cert.subject or 'n/a'}", f"Issuer: {cert.issuer or 'n/a'}"]
    if cert.altnames:
        lines.append(f"Subject Alternative Names: {cert.altnames}")
    if cert.signature_algorithm:
        lines.append(f"Signature Algorithm: {cert.signature_algorithm}")
    if cert.pk_type:
        key = cert.pk_type
        if cert.pk_bits:
            key += f" {cert.pk_bits}-bit"
        if cert.pk_curve:
            key += f" (curve {cert.pk_curve})"
        lines.append(f"Public Key: {key}")
    if cert.not_valid_before:
        lines.append(f"Valid From: {cert.not_valid_before}")
    if cert.not_valid_after:
        lines.append(f"Valid Until: {cert.not_valid_after}")
    # Only ever appended when true -- see module docstring on why a false "not expired"/
    # "not self-signed" line would corrupt the Correlation Engine's plain substring match.
    if cert.self_signed:
        lines.append("This certificate is self-signed.")
    if cert.expired:
        lines.append("This certificate is expired.")
    if cert.not_yet_valid:
        lines.append("This certificate is not yet valid.")
    return "\n".join(lines)


def _normalize_observations(host: SslscanHost, *, host_index: int) -> list[NormalizedObservation]:
    endpoint = f"{host.sni_name or host.host}:{host.port}" if host.port else (host.sni_name or host.host)
    observations = [
        NormalizedObservation(
            source="sslscan-enum-ciphers",
            title=f"SSLScan: TLS Protocols & Cipher Suites ({endpoint})",
            detail=_protocols_and_ciphers_detail(host),
            host_index=host_index,
            port=host.port or None,
            category=ObservationCategory.TLS.value,
            observation_type="sslscan-enum-ciphers",
        )
    ]
    for cert_index, cert in enumerate(host.certificates):
        label = "Certificate" if len(host.certificates) == 1 else f"Certificate #{cert_index + 1} ({cert.cert_type})"
        observations.append(
            NormalizedObservation(
                source="sslscan-cert",
                title=f"SSLScan: {label} ({endpoint})",
                detail=_certificate_detail(cert),
                host_index=host_index,
                port=host.port or None,
                category=ObservationCategory.TLS.value,
                observation_type="sslscan-cert",
            )
        )
    return observations
