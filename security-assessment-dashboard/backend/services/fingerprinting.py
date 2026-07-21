"""Deterministic merge-key computation for the Host Inventory & Observation Engine.

Pure, side-effect-free functions with no database access — the sole purpose
of this module is "given the same facts, always compute the same key," so
:class:`~backend.services.host_inventory_service.HostInventoryService` can
look up "have I seen this host/service/observation before" with a plain
indexed equality query instead of any fuzzy matching.

Each fingerprint is a ``namespace:sha256hexdigest`` string. The namespace
prefix means two different *kinds* of identity (e.g. a MAC address that
happens to share bytes with an IP string) can never collide, and it also
records *which* signal was actually used to identify the host — useful for
debugging a merge decision later.

Priority order per the phase brief's "Fingerprint Matching" section:

- **Host** (:func:`host_fingerprint`): MAC address > IPv4/IPv6 > hostname —
  a MAC is the most stable identity signal (survives DHCP address changes on
  the same L2 segment); hostname is the last resort for domain-only targets
  with no resolved IP yet.
- **Service** (:func:`service_fingerprint`): the owning host's fingerprint +
  port + protocol — a service only exists in the context of one host.
- **Observation** (:func:`observation_fingerprint`): plugin + the owning
  host's fingerprint + category + observation_type + title.
"""

import hashlib

from backend.models.enums import NetworkProtocol


def _digest(namespace: str, *parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return f"{namespace}:{hashlib.sha256(payload).hexdigest()}"


def host_fingerprint(
    *,
    mac_address: str | None,
    ipv4: str | None,
    ipv6: str | None,
    hostname: str | None,
) -> str:
    """Compute a host's deterministic merge key: MAC > IPv4/IPv6 > hostname.

    Raises ``ValueError`` if every identity signal is missing — a plugin
    that reports a host with no address and no hostname at all has
    nothing to merge on, which should surface as a normalization bug, not
    silently produce a fingerprint that could collide with another host.
    """
    if mac_address:
        return _digest("mac", mac_address.lower())
    if ipv4:
        return _digest("ipv4", ipv4)
    if ipv6:
        return _digest("ipv6", ipv6)
    if hostname:
        return _digest("hostname", hostname.lower())
    raise ValueError("Cannot compute a host fingerprint with no MAC address, IP, or hostname.")


def service_fingerprint(*, host_fingerprint_value: str, port: int, protocol: NetworkProtocol) -> str:
    """Compute a service's deterministic merge key, scoped to its owning host."""
    return _digest("service", host_fingerprint_value, str(port), protocol.value)


def observation_fingerprint(
    *,
    plugin: str,
    host_fingerprint_value: str,
    category: str,
    observation_type: str | None,
    title: str,
) -> str:
    """Compute an observation's deterministic merge key, scoped to its owning host."""
    return _digest("observation", plugin, host_fingerprint_value, category, observation_type or "", title)


def finding_fingerprint(*, rule_id: str, host_fingerprint_value: str) -> str:
    """Compute a finding's deterministic merge key: one rule fires at most once per host.

    Re-running the Correlation Engine against the same host re-evaluates
    every rule and lands on this same key -- "merge duplicates" from the
    phase brief -- rather than inserting a second ``Finding`` row for a
    condition that was already recorded.
    """
    return _digest("finding", rule_id, host_fingerprint_value)
