"""Target value validation and normalization.

Pure, side-effect-free functions with no I/O and no database access — used
by both ``TargetService`` (create/update/bulk-import) and the standalone
target-validation API endpoint, so this validation logic exists in exactly
one place. Built entirely on the standard library (``ipaddress``,
``urllib.parse``, ``re``): no new dependency is needed for IPv4/IPv6/CIDR/
hostname/domain/URL validation.
"""

import ipaddress
import re
from collections.abc import Callable
from urllib.parse import urlparse, urlunparse

from backend.models.enums import TargetType

_HOSTNAME_LABEL = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")
_MAX_HOSTNAME_LENGTH = 253


class TargetValidationError(ValueError):
    """Raised when a raw target value fails validation for its declared type."""


def _validate_hostname_format(value: str) -> None:
    if not value or len(value) > _MAX_HOSTNAME_LENGTH:
        raise TargetValidationError("Hostname must be 1-253 characters long.")
    for label in value.split("."):
        if not _HOSTNAME_LABEL.match(label):
            raise TargetValidationError(
                f"'{label}' is not a valid hostname label (letters, digits, hyphens; "
                "1-63 characters; cannot start or end with a hyphen)."
            )


def validate_ipv4(value: str) -> str:
    """Validate an IPv4 address and return its canonical string form."""
    try:
        return str(ipaddress.IPv4Address(value.strip()))
    except ValueError as exc:
        raise TargetValidationError(f"'{value}' is not a valid IPv4 address.") from exc


def validate_ipv6(value: str) -> str:
    """Validate an IPv6 address and return its canonical (compressed) string form."""
    try:
        return str(ipaddress.IPv6Address(value.strip()))
    except ValueError as exc:
        raise TargetValidationError(f"'{value}' is not a valid IPv6 address.") from exc


def validate_cidr(value: str) -> str:
    """Validate an IPv4 or IPv6 CIDR range and return its canonical network form.

    Host bits are masked automatically (``strict=False``), e.g.
    ``192.168.1.5/24`` normalizes to ``192.168.1.0/24``.
    """
    try:
        network = ipaddress.ip_network(value.strip(), strict=False)
    except ValueError as exc:
        raise TargetValidationError(f"'{value}' is not a valid CIDR range.") from exc
    return str(network)


def validate_hostname(value: str) -> str:
    """Validate a hostname (single label or multi-label, no public-suffix requirement)."""
    normalized = value.strip().rstrip(".").lower()
    _validate_hostname_format(normalized)
    return normalized


def validate_domain(value: str) -> str:
    """Validate a fully qualified domain name (hostname format, at least two labels)."""
    normalized = value.strip().rstrip(".").lower()
    _validate_hostname_format(normalized)
    if "." not in normalized:
        raise TargetValidationError(f"'{value}' is not a fully qualified domain (expected at least one '.').")
    return normalized


def validate_url(value: str) -> str:
    """Validate an http(s) URL and return it with a lowercased scheme/host."""
    stripped = value.strip()
    parsed = urlparse(stripped)
    if parsed.scheme not in ("http", "https"):
        raise TargetValidationError(f"'{value}' must start with http:// or https://.")
    if not parsed.netloc:
        raise TargetValidationError(f"'{value}' is missing a host.")
    normalized = parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower())
    return urlunparse(normalized)


_VALIDATORS: dict[TargetType, Callable[[str], str]] = {
    TargetType.IPV4: validate_ipv4,
    TargetType.IPV6: validate_ipv6,
    TargetType.CIDR: validate_cidr,
    TargetType.HOSTNAME: validate_hostname,
    TargetType.DOMAIN: validate_domain,
    TargetType.URL: validate_url,
}


def validate_target(target_type: TargetType, raw_value: str) -> str:
    """Validate and normalize ``raw_value`` for ``target_type``.

    Returns the normalized value. Raises :class:`TargetValidationError` with
    a human-readable message if the value is invalid for that type.
    """
    if not raw_value or not raw_value.strip():
        raise TargetValidationError("Target value must not be empty.")
    return _VALIDATORS[target_type](raw_value)


def detect_target_type(raw_value: str) -> TargetType | None:
    """Best-effort auto-detection of a target's type from its raw string.

    Used by bulk import (TXT has no type column) when the caller hasn't
    specified one. Returns ``None`` only for an empty/whitespace value.
    """
    value = raw_value.strip()
    if not value:
        return None

    try:
        ipaddress.IPv4Address(value)
        return TargetType.IPV4
    except ValueError:
        pass

    try:
        ipaddress.IPv6Address(value)
        return TargetType.IPV6
    except ValueError:
        pass

    if "/" in value:
        try:
            ipaddress.ip_network(value, strict=False)
            return TargetType.CIDR
        except ValueError:
            pass

    if "://" in value:
        return TargetType.URL

    if "." in value.rstrip("."):
        return TargetType.DOMAIN

    return TargetType.HOSTNAME
