"""Output parsing for SSLScan. Its ``--xml=-`` output is XML.

Field names below were verified against real ``sslscan 2.1.5`` output
(``<document><ssltest host=... port=...><protocol/><fallback/>
<renegotiation/><compression/><heartbleed/><cipher/><group/>
<certificates><certificate>...</certificate></certificates></ssltest></document>``)
-- not guessed from documentation, since a minor sslscan version could
otherwise silently produce zero parsed results. Every attribute lookup
still uses ``Element.get()``/``.find()`` defensively (missing attribute ->
``None``/empty, never a ``KeyError``) so an older/newer sslscan build that
omits an optional element degrades gracefully instead of crashing the job.
"""

from dataclasses import dataclass, field
from xml.etree.ElementTree import Element

from backend.plugins.models.execution import PluginRawOutput
from backend.plugins.sdk import safe_xml_parse


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true")


def _int(value: str | None) -> int | None:
    return int(value) if value and value.strip().lstrip("-").isdigit() else None


@dataclass(frozen=True)
class SslProtocol:
    """One ``<protocol type="ssl|tls" version="..." enabled="0|1"/>`` probe result."""

    protocol_type: str
    version: str
    enabled: bool


@dataclass(frozen=True)
class SslCipher:
    """One ``<cipher status="preferred|accepted|rejected" .../>`` entry."""

    status: str
    ssl_version: str
    bits: int
    cipher: str
    cipher_id: str | None = None
    strength: str | None = None
    curve: str | None = None
    ecdhe_bits: int | None = None


@dataclass(frozen=True)
class SslGroup:
    """One ``<group .../>`` key-exchange group SSLScan negotiated."""

    ssl_version: str
    bits: int
    name: str
    group_id: str | None = None


@dataclass(frozen=True)
class SslCertificate:
    """One ``<certificate type="short|full">`` block under ``<certificates>``."""

    cert_type: str
    signature_algorithm: str | None = None
    pk_type: str | None = None
    pk_bits: int | None = None
    pk_curve: str | None = None
    subject: str | None = None
    altnames: str | None = None
    issuer: str | None = None
    self_signed: bool = False
    not_valid_before: str | None = None
    not_yet_valid: bool = False
    not_valid_after: str | None = None
    expired: bool = False


@dataclass(frozen=True)
class SslscanHost:
    """One ``<ssltest host=... sniname=... port=...>`` result block."""

    host: str
    sni_name: str | None
    port: int
    protocols: list[SslProtocol] = field(default_factory=list)
    fallback_supported: bool | None = None
    renegotiation_supported: bool | None = None
    renegotiation_secure: bool | None = None
    compression_supported: bool | None = None
    #: SSLScan's own ``sslversion`` attribute (e.g. "TLSv1.2") -> ``vulnerable`` flag.
    heartbleed: dict[str, bool] = field(default_factory=dict)
    ciphers: list[SslCipher] = field(default_factory=list)
    groups: list[SslGroup] = field(default_factory=list)
    certificates: list[SslCertificate] = field(default_factory=list)


@dataclass(frozen=True)
class SslscanScanResult:
    hosts: list[SslscanHost]


def _parse_protocol(el: Element) -> SslProtocol:
    return SslProtocol(protocol_type=el.get("type", ""), version=el.get("version", ""), enabled=_bool(el.get("enabled")))


def _parse_cipher(el: Element) -> SslCipher:
    return SslCipher(
        status=el.get("status", ""),
        ssl_version=el.get("sslversion", ""),
        bits=_int(el.get("bits")) or 0,
        cipher=el.get("cipher", ""),
        cipher_id=el.get("id") or None,
        strength=el.get("strength") or None,
        curve=el.get("curve") or None,
        ecdhe_bits=_int(el.get("ecdhebits")),
    )


def _parse_group(el: Element) -> SslGroup:
    return SslGroup(
        ssl_version=el.get("sslversion", ""), bits=_int(el.get("bits")) or 0, name=el.get("name", ""), group_id=el.get("id") or None
    )


def _child_text(el: Element, tag: str) -> str | None:
    child = el.find(tag)
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    return text or None


def _parse_certificate(el: Element) -> SslCertificate:
    pk = el.find("pk")
    return SslCertificate(
        cert_type=el.get("type", "short"),
        signature_algorithm=_child_text(el, "signature-algorithm"),
        pk_type=pk.get("type") if pk is not None else None,
        pk_bits=_int(pk.get("bits")) if pk is not None else None,
        pk_curve=(pk.get("curve_name") or pk.get("curve")) if pk is not None else None,
        subject=_child_text(el, "subject"),
        altnames=_child_text(el, "altnames"),
        issuer=_child_text(el, "issuer"),
        self_signed=_bool(_child_text(el, "self-signed")),
        not_valid_before=_child_text(el, "not-valid-before"),
        not_yet_valid=_bool(_child_text(el, "not-yet-valid")),
        not_valid_after=_child_text(el, "not-valid-after"),
        expired=_bool(_child_text(el, "expired")),
    )


def _parse_host(el: Element) -> SslscanHost:
    heartbleed: dict[str, bool] = {}
    for hb_el in el.findall("heartbleed"):
        heartbleed[hb_el.get("sslversion", "")] = _bool(hb_el.get("vulnerable"))

    fallback_el = el.find("fallback")
    renegotiation_el = el.find("renegotiation")
    compression_el = el.find("compression")
    certificates = [
        _parse_certificate(cert_el) for certs_el in el.findall("certificates") for cert_el in certs_el.findall("certificate")
    ]

    return SslscanHost(
        host=el.get("host", ""),
        sni_name=el.get("sniname") or None,
        port=_int(el.get("port")) or 0,
        protocols=[_parse_protocol(p) for p in el.findall("protocol")],
        fallback_supported=_bool(fallback_el.get("supported")) if fallback_el is not None else None,
        renegotiation_supported=_bool(renegotiation_el.get("supported")) if renegotiation_el is not None else None,
        renegotiation_secure=_bool(renegotiation_el.get("secure")) if renegotiation_el is not None else None,
        compression_supported=_bool(compression_el.get("supported")) if compression_el is not None else None,
        heartbleed=heartbleed,
        ciphers=[_parse_cipher(c) for c in el.findall("cipher")],
        groups=[_parse_group(g) for g in el.findall("group")],
        certificates=certificates,
    )


def parse_sslscan_output(raw_output: PluginRawOutput) -> SslscanScanResult | None:
    root = safe_xml_parse(raw_output.stdout)
    if root is None:
        return None
    hosts = [_parse_host(el) for el in root.findall("ssltest")]
    if not hosts:
        return None
    return SslscanScanResult(hosts=hosts)
