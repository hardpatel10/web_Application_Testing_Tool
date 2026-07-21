"""Abstract base class every tool plugin must extend.

Per ``.claude/CLAUDE.md``'s plugin philosophy, a plugin only detects
installation, executes the tool, and captures/parses/normalizes its output —
it never touches the database, renders UI, generates reports, or correlates
findings. This class is the enforced shape of that boundary: it has no
constructor dependency on a DB session, an HTTP request, or any rendering
concern, so a conforming subclass architecturally cannot reach into those
layers through its base class.
"""

from abc import ABC, abstractmethod

from backend.models.enums import TargetType
from backend.plugins.models.config import PluginConfiguration
from backend.plugins.models.execution import PluginExecutionContext, PluginRawOutput
from backend.plugins.models.health import PluginHealth
from backend.plugins.models.manifest import PluginManifest
from backend.plugins.models.metadata import PluginMetadata


class BasePlugin(ABC):
    """Contract every plugin implements.

    Instantiated by :class:`~backend.plugins.loader.plugin_loader.PluginLoader`
    with the manifest parsed from that plugin's ``plugin.json`` and its
    (initially default) :class:`PluginConfiguration`.
    """

    def __init__(self, manifest: PluginManifest, config: PluginConfiguration | None = None) -> None:
        self._manifest = manifest
        self._config = config or PluginConfiguration()

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    @property
    def config(self) -> PluginConfiguration:
        return self._config

    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return this plugin's identity and declared capabilities."""

    @abstractmethod
    def health(self) -> PluginHealth:
        """Return this plugin's current installation/readiness status."""

    @abstractmethod
    def check_installation(self) -> bool:
        """Return whether this plugin's required binaries are present."""

    @abstractmethod
    def get_version(self) -> str | None:
        """Return the detected installed tool version, if determinable."""

    @abstractmethod
    def validate_target(self, target_type: TargetType, target_value: str) -> bool:
        """Return whether this plugin can run against the given target."""

    @abstractmethod
    def prepare(self, context: PluginExecutionContext) -> None:
        """Perform any setup needed before a command can be built (e.g. output dirs)."""

    @abstractmethod
    def build_command(self, context: PluginExecutionContext) -> list[str]:
        """Return the argv this plugin would execute for the given context."""

    @abstractmethod
    async def execute(self, command: list[str], context: PluginExecutionContext) -> PluginRawOutput:
        """Run ``command`` and return its captured raw output.

        Async so a real implementation can await
        :func:`backend.plugins.sdk.process_runner.run_subprocess` (or an
        equivalent ``asyncio.create_subprocess_exec`` call) without blocking
        the event loop the execution engine (:mod:`backend.execution`) runs
        on — the engine awaits this directly, it never wraps it in a thread.
        """

    @abstractmethod
    def parse(self, raw_output: PluginRawOutput) -> object:
        """Parse raw output into a tool-specific intermediate structure."""

    @abstractmethod
    def normalize(self, parsed_output: object) -> object:
        """Normalize parsed output into the platform's common shape."""

    @abstractmethod
    def cleanup(self, context: PluginExecutionContext) -> None:
        """Release any resources (temp files, handles) created during execution."""
