"""Web Rules: recognize HTTP/HTTPS services from Nmap's own port/service-name detection.

A pragmatic, honest heuristic over what ``Service`` already carries (``port``,
``service_name`` -- Nmap's own ``-sV`` service-name guess) -- not a redesign
of Nmap parsing. Ports match the Assessment Pipeline brief's own worked
examples (80/8080/443/8443) plus Nmap's well-known alternate-port service
names, so a scan against a non-standard port Nmap itself still identified as
HTTP(S) is recognized too.
"""

from backend.correlation.text_utils import contains_any
from backend.models.discovered_host import DiscoveredHost
from backend.models.enums import PortState
from backend.models.service import Service
from backend.pipeline.base import PipelineRule
from backend.pipeline.endpoint_generator import generate_endpoint
from backend.pipeline.models import PipelineDecision, ScheduleDecision

_FOLLOW_UP_TOOLS: tuple[str, ...] = ("nikto", "nuclei")

_HTTPS_PORTS = {443, 8443}
_HTTPS_SERVICE_NAME_HINTS = ("https", "ssl/http")

_HTTP_PORTS = {80, 8080, 8000, 8008, 8880}
_HTTP_SERVICE_NAME_HINTS = ("http", "www")


class HttpsServiceRule(PipelineRule):
    """An HTTPS-looking service -> schedule Nikto + Nuclei at ``https://host[:port]``."""

    rule_id = "PIPE-HTTPS-001"
    description = "Open HTTPS-looking service (standard/alternate HTTPS port or an https/ssl service-name match)."

    def evaluate(self, service: Service, host: DiscoveredHost) -> PipelineDecision:
        if service.state != PortState.OPEN:
            return None
        name = (service.service_name or "").lower()
        if service.port not in _HTTPS_PORTS and not contains_any(name, _HTTPS_SERVICE_NAME_HINTS):
            return None
        return ScheduleDecision(
            tool_names=_FOLLOW_UP_TOOLS, endpoint=generate_endpoint(host, service, scheme="https")
        )


class HttpServiceRule(PipelineRule):
    """A plain HTTP-looking service -> schedule Nikto + Nuclei at ``http://host[:port]``."""

    rule_id = "PIPE-HTTP-001"
    description = "Open HTTP-looking service (standard/alternate HTTP port or an http service-name match)."

    def evaluate(self, service: Service, host: DiscoveredHost) -> PipelineDecision:
        if service.state != PortState.OPEN:
            return None
        name = (service.service_name or "").lower()
        # "http" is a substring of "https"/"ssl/http" -- explicitly exclude those so this rule
        # is correct standalone (not merely correct-by-registry-ordering). Caught by this
        # module's own test: a bare `contains_any(name, ("http",))` matched service_name="https" too.
        if contains_any(name, _HTTPS_SERVICE_NAME_HINTS):
            return None
        if service.port not in _HTTP_PORTS and not contains_any(name, _HTTP_SERVICE_NAME_HINTS):
            return None
        return ScheduleDecision(
            tool_names=_FOLLOW_UP_TOOLS, endpoint=generate_endpoint(host, service, scheme="http")
        )


RULES: tuple[type[PipelineRule], ...] = (
    HttpsServiceRule,
    HttpServiceRule,
)
