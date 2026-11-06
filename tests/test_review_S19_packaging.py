"""S19 review regressions: provider keys stripped by every check, clean packages, UTF-8 text IO,
and escaped evidence keys in the app's markup. Nothing here downloads or runs a provider."""

from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest

from deploy_workflow.model.adapter import KEY_VARIABLES

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps/issuer-library"


def load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_strips_every_provider_key_including_copilot():
    validate = load("review_validate", APP / "validate.py")
    assert set(validate.KEYS) == {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "COPILOT_GITHUB_TOKEN",
    }
    assert set(validate.KEYS) == set(KEY_VARIABLES.values())


@pytest.mark.parametrize(
    "script", ["validate.py", "packaging/smoke_test.py", "designs/browser_check.py"]
)
def test_no_check_keeps_its_own_copy_of_the_key_list(script):
    text = (APP / script).read_text(encoding="utf-8")
    assert "from deploy_workflow.model.adapter import KEY_VARIABLES" in text
    assert "KEY_VARIABLES.values()" in text
    assert "OPENROUTER_API_KEY" not in text, "a hand-copied provider key list remains"


def test_clear_keeps_only_the_named_entries(tmp_path):
    runtime = load("review_runtime", APP / "packaging/runtime.py")
    (tmp_path / "engine/runtime").mkdir(parents=True)
    (tmp_path / "engine/runtime/python.exe").write_bytes(b"MZ")
    (tmp_path / "engine/stale.py").write_text("old engine file", encoding="utf-8")
    (tmp_path / "engine/src/old_pkg").mkdir(parents=True)
    (tmp_path / "README.md").write_text("old", encoding="utf-8")
    runtime.clear(tmp_path, {"engine"})
    runtime.clear(tmp_path / "engine", {"runtime"})
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")) == [
        "engine",
        "engine/runtime",
        "engine/runtime/python.exe",
    ]
    runtime.clear(tmp_path / "missing", set())  # A first build has no folder yet.


def test_a_reused_runtime_is_the_only_thing_kept_from_an_earlier_build(tmp_path):
    runtime = load("review_runtime_bundle", APP / "packaging/runtime.py")
    engine = tmp_path / "engine"
    (engine / "runtime").mkdir(parents=True)
    (engine / "runtime/python.exe").write_bytes(b"MZ")
    (engine / "stale_module.py").write_text("removed upstream", encoding="utf-8")
    (engine / "src/removed_package").mkdir(parents=True)
    records = {
        "python": {"version": "3.13.15", "sha256": runtime.PYTHON["amd64"]},
        "wheels": {name: {"version": version} for name, version in runtime.PINS.items()},
    }
    (engine / "runtime-manifest.json").write_text(json.dumps(records), encoding="utf-8")
    runtime.bundle(tmp_path, "amd64")
    assert not (engine / "stale_module.py").exists()
    assert not (engine / "src/removed_package").exists()
    assert (engine / "runtime/python.exe").read_bytes() == b"MZ"
    assert (engine / "src/issuer_library/server.py").is_file()
    assert (engine / "store.py").read_bytes() == (APP / "engine/store.py").read_bytes()


def test_a_changed_pin_starts_the_runtime_from_empty(tmp_path, monkeypatch):
    runtime = load("review_runtime_fresh", APP / "packaging/runtime.py")
    engine = tmp_path / "engine"
    (engine / "runtime/Lib/site-packages/pydantic-2.0.0.dist-info").mkdir(parents=True)
    (engine / "runtime/python.exe").write_bytes(b"MZ")
    stale = {"python": {"sha256": "other"}, "wheels": {}}
    (engine / "runtime-manifest.json").write_text(json.dumps(stale), encoding="utf-8")

    class Offline(Exception):
        pass

    def no_download(url, sha, name):
        assert not (engine / "runtime-manifest.json").exists()
        assert not (engine / "runtime/Lib").exists(), "an older wheel would survive"
        raise Offline

    monkeypatch.setattr(runtime, "download", no_download)
    with pytest.raises(Offline):
        runtime.bundle(tmp_path, "amd64")


TEXT_CALLS = {"read_text", "write_text"}


@pytest.mark.parametrize(
    "script",
    [
        "packaging/sync_assets.py",
        "packaging/runtime.py",
        "packaging/smoke_test.py",
        "designs/build.py",
    ],
)
def test_build_scripts_name_utf8_for_every_text_file(script):
    tree = ast.parse((APP / script).read_text(encoding="utf-8"))
    missing = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in TEXT_CALLS
        and not any(k.arg == "encoding" for k in node.keywords)
    ]
    assert missing == [], f"{script}: text IO without encoding at lines {missing}"


EVIDENCE = re.compile(r'data-evidence="\$\{(?!esc\()')
UNESCAPED_CELL = re.compile(r">\$\{p\.(?:exact|label)\}<")


@pytest.mark.parametrize("script", ["web/views.js", "web/screen.js"])
def test_evidence_keys_and_chart_cells_are_escaped_in_markup(script):
    text = (APP / script).read_text(encoding="utf-8")
    assert EVIDENCE.findall(text) == [], "an evidence key is interpolated unescaped"
    assert UNESCAPED_CELL.findall(text) == [], "a retained table cell is inserted as markup"
