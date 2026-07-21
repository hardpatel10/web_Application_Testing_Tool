"""Tests for the plugin framework: discovery/loader/registry unit behavior
plus the /api/v1/plugins endpoints against the real, non-executing
ExamplePlugin.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient

from backend.plugins.core.base_plugin import BasePlugin
from backend.plugins.exceptions import PluginNotFoundError, PluginValidationError
from backend.plugins.loader.plugin_loader import PluginLoader
from backend.plugins.registry.plugin_registry import PluginRegistry
from backend.plugins.validators.interface_validator import validate_interface

EXAMPLE_PLUGIN_ID = "example-plugin"


# --- API-level tests, against the real example-plugin -----------------------


async def test_list_plugins_includes_example_plugin(client: AsyncClient) -> None:
    response = await client.get("/api/v1/plugins")

    assert response.status_code == 200
    ids = [plugin["id"] for plugin in response.json()]
    assert EXAMPLE_PLUGIN_ID in ids


async def test_get_plugin_detail(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/plugins/{EXAMPLE_PLUGIN_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == EXAMPLE_PLUGIN_ID
    assert body["validation_valid"] is True
    assert body["required_binaries"] == []
    assert body["missing_dependencies"] == []


async def test_get_plugin_health(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/plugins/{EXAMPLE_PLUGIN_ID}/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["installed"] is True


async def test_validate_plugin(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/plugins/{EXAMPLE_PLUGIN_ID}/validate")

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["errors"] == []


async def test_reload_plugins_rediscovers_example_plugin(client: AsyncClient) -> None:
    response = await client.post("/api/v1/plugins/reload")

    assert response.status_code == 200
    body = response.json()
    assert body["registered_count"] >= 1
    assert any(plugin["id"] == EXAMPLE_PLUGIN_ID for plugin in body["plugins"])
    assert body["failures"] == []


async def test_get_unknown_plugin_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/plugins/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# --- Framework unit tests, isolated from the real plugins/ directory --------


@pytest.fixture
def tmp_plugins_root() -> Path:
    directory = Path(tempfile.mkdtemp(prefix="plugin_test_"))
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


def _write_required_files(plugin_dir: Path, *, plugin_json: str) -> None:
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(plugin_json, encoding="utf-8")
    (plugin_dir / "plugin.py").write_text("", encoding="utf-8")
    (plugin_dir / "parser.py").write_text("", encoding="utf-8")
    (plugin_dir / "normalizer.py").write_text("", encoding="utf-8")
    (plugin_dir / "validator.py").write_text("", encoding="utf-8")
    (plugin_dir / "README.md").write_text("stub", encoding="utf-8")


def test_loader_ignores_directory_missing_required_files(tmp_plugins_root: Path) -> None:
    (tmp_plugins_root / "broken_plugin").mkdir()

    results = PluginLoader(tmp_plugins_root).discover()

    assert len(results) == 1
    assert results[0].success is False
    assert "plugin.json" in results[0].error


def test_loader_ignores_directory_with_malformed_manifest(tmp_plugins_root: Path) -> None:
    _write_required_files(tmp_plugins_root / "broken_plugin", plugin_json="{not valid json")

    results = PluginLoader(tmp_plugins_root).discover()

    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error is not None


def test_loader_reports_missing_entrypoint_module(tmp_plugins_root: Path) -> None:
    manifest = """
    {
        "id": "missing-entry",
        "name": "Missing Entry",
        "version": "1.0.0",
        "entrypoint": "plugin:MissingEntryPlugin",
        "author": "Test",
        "description": "Manifest is valid but plugin.py never defines the class.",
        "license": "MIT",
        "homepage": null,
        "documentation_url": null,
        "supported_platforms": ["linux"],
        "supported_targets": ["hostname"],
        "supported_output_formats": ["json"],
        "required_binaries": [],
        "dependencies": []
    }
    """
    _write_required_files(tmp_plugins_root / "missing_entry", plugin_json=manifest)

    results = PluginLoader(tmp_plugins_root).discover()

    assert len(results) == 1
    assert results[0].success is False
    assert "MissingEntryPlugin" in results[0].error


def test_registry_rejects_duplicate_plugin_ids() -> None:
    registry = PluginRegistry()
    first = _fake_registered_plugin("dup-id")
    second = _fake_registered_plugin("dup-id")

    registry.register(first)
    with pytest.raises(PluginValidationError):
        registry.register(second)


def test_registry_raises_not_found_for_unknown_id() -> None:
    registry = PluginRegistry()
    with pytest.raises(PluginNotFoundError):
        registry.get("nonexistent")


def test_registry_enable_disable_round_trip() -> None:
    registry = PluginRegistry()
    registry.register(_fake_registered_plugin("toggle-me"))

    assert registry.is_enabled("toggle-me") is True
    registry.disable("toggle-me")
    assert registry.is_enabled("toggle-me") is False
    registry.enable("toggle-me")
    assert registry.is_enabled("toggle-me") is True


def test_registry_check_dependencies_reports_missing() -> None:
    registry = PluginRegistry()
    dependent = _fake_registered_plugin("dependent-plugin", dependencies=["missing-dependency"])
    registry.register(dependent)

    assert registry.check_dependencies("dependent-plugin") == ["missing-dependency"]


def test_interface_validator_rejects_incomplete_subclass() -> None:
    class IncompletePlugin(BasePlugin):
        def metadata(self):
            return None

    result = validate_interface(IncompletePlugin)

    assert result.valid is False
    assert any("health" in error for error in result.errors)


def _fake_registered_plugin(plugin_id: str, *, dependencies: list[str] | None = None):
    """Build a minimal RegisteredPlugin for registry-only unit tests.

    Uses the real ExamplePlugin class as the ``instance`` (it needs no
    external dependency), only varying the manifest id/dependencies under
    test.
    """
    from datetime import datetime, timezone

    from backend.plugins.models.manifest import PluginManifest
    from backend.plugins.models.validation import PluginValidationResult
    from backend.plugins.plugins.example_plugin.plugin import ExamplePlugin
    from backend.plugins.registry.registered_plugin import RegisteredPlugin

    manifest = PluginManifest(
        id=plugin_id,
        name="Fake Plugin",
        version="1.0.0",
        entrypoint="plugin:ExamplePlugin",
        author="Test",
        description="Fake manifest for registry unit tests.",
        license="MIT",
        supported_platforms=["linux"],
        supported_targets=["hostname"],
        supported_output_formats=["json"],
        required_binaries=[],
        dependencies=dependencies or [],
    )
    return RegisteredPlugin(
        manifest=manifest,
        instance=ExamplePlugin(manifest),
        source_path=Path("/nonexistent"),
        validation=PluginValidationResult(valid=True),
        loaded_at=datetime.now(timezone.utc),
    )
