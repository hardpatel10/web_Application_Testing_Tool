"""Path/entrypoint helpers used by the loader."""

from pathlib import Path


def manifest_path(plugin_directory: Path) -> Path:
    """Return the expected ``plugin.json`` path for a plugin directory."""
    return plugin_directory / "plugin.json"


def split_entrypoint(entrypoint: str) -> tuple[str, str]:
    """Split a manifest ``entrypoint`` string into ``(module_stem, class_name)``.

    Format is ``'<module_stem>:<ClassName>'`` (e.g. ``'plugin:ExamplePlugin'``),
    already validated by :class:`~backend.plugins.models.manifest.PluginManifest`.
    """
    module_stem, _, class_name = entrypoint.partition(":")
    return module_stem, class_name


def entrypoint_module_path(plugin_directory: Path, entrypoint: str) -> Path:
    """Return the ``.py`` file an ``entrypoint`` string refers to."""
    module_stem, _ = split_entrypoint(entrypoint)
    return plugin_directory / f"{module_stem}.py"
