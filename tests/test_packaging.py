"""Credit OS package build: the layout, launcher, version stamp and wheels, built for real."""

import hashlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Self

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / "apps/issuer-library/packaging"
COMPANY_PYTHON = r"C:\Program Files\Statestreet\Python313\pythonw.exe"


def load_build() -> ModuleType:
    spec = importlib.util.spec_from_file_location("credit_os_build", PACKAGING / "build.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    target = tmp_path_factory.mktemp("package") / "CreditOS"
    release = load_build().build(target)
    return target, release


def export_pins() -> set[str]:
    out = subprocess.run(
        [
            "uv",
            "export",
            "--locked",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {
        line.split("==")[0].lower().replace("_", "-") + "-" + line.split("==")[1].split()[0]
        for line in out.splitlines()
        if re.match(r"^[A-Za-z0-9._-]+==", line)
    }


def test_package_holds_no_executable(built: tuple[Path, Path]) -> None:
    target, _ = built
    assert [p for p in target.rglob("*") if p.suffix.lower() in {".exe", ".dll"}] == []


def test_launcher_runs_company_python_on_this_release(built: tuple[Path, Path]) -> None:
    target, release = built
    version = release.name
    raw = (target / "Credit OS.cmd").read_bytes()
    assert raw.count(b"\r\n") == raw.count(b"\n")
    text = raw.decode("ascii")
    lines = text.split("\r\n")
    named = [line for line in lines if version in line]
    assert len(named) == 1
    assert f'"{COMPANY_PYTHON}" -I -B -X utf8 "%~dp0app\\{version}\\start.py"' in named[0]
    assert "if exist %6" in text
    for check, subject in (("if exist %1 ", "company Python"), ("if exist %6 ", "missing")):
        at = next(i for i, line in enumerate(lines) if line.startswith(check))
        message = lines[at + 1]
        assert message.startswith("echo ") and subject in message, (check, message)
    assert 'start "Credit OS"' in text


def test_release_has_sdk_and_server_closure(built: tuple[Path, Path]) -> None:
    _, release = built
    lib = release / "lib"
    for name in ("copilot", "pydantic_core", "fastapi", "uvicorn"):
        assert (lib / name).is_dir(), name
    assert list((lib / "pydantic_core").glob("*.cp313-win_amd64.pyd"))


def test_version_is_stamped_and_read(built: tuple[Path, Path]) -> None:
    _, release = built
    stamp = (release / "engine/VERSION").read_text().strip()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    assert re.fullmatch(r"\d{4}\.\d{2}\.\d{2}-[0-9a-f]{12}", stamp)
    assert stamp == release.name
    assert stamp.split("-")[1] == head[:12]
    code = "import issuer_library.version as v; print(v.app_version())"
    ran = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            f"import sys; sys.path.insert(0, {str(release / 'engine/src')!r}); {code}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert ran.stdout.strip() == stamp
    sys.path.insert(0, str(ROOT / "src"))
    try:
        from issuer_library.version import app_version

        assert app_version() == "dev"
    finally:
        sys.path.remove(str(ROOT / "src"))


def test_start_py_runs_isolated(built: tuple[Path, Path]) -> None:
    _, release = built
    ran = subprocess.run(
        [sys.executable, "-I", "-B", "-X", "utf8", str(release / "start.py"), "--version"],
        env={},
        check=True,
        capture_output=True,
        text=True,
    )
    assert ran.stdout.strip() == (release / "engine/VERSION").read_text().strip()


def test_default_workspace_example(built: tuple[Path, Path]) -> None:
    target, _ = built
    example = json.loads((target / "default-workspace.json.example").read_text())
    assert example == {"workspace": "\\\\server\\share\\CreditOS\\workspace"}
    assert not (target / "default-workspace.json").exists()


def test_wheels_come_from_the_export(built: tuple[Path, Path]) -> None:
    _, release = built
    stamped = {
        p.name.removesuffix(".dist-info").lower().replace("_", "-")
        for p in (release / "lib").glob("*.dist-info")
    }
    assert stamped == export_pins()


def test_release_layout(built: tuple[Path, Path]) -> None:
    _, release = built
    for name in (
        "start.py",
        "engine/bridge.py",
        "engine/store.py",
        "engine/library_manifest.py",
        "engine/catalog.json",
        "engine/smoke-context.json",
        "engine/src/issuer_library/__main__.py",
        "web/index.html",
        "Smoke-test.ps1",
    ):
        assert (release / name).is_file(), name
    assert not list((release / "engine/src").rglob("__pycache__"))


PROBE = """
import importlib.util, runpy, sys
try:
    runpy.run_path(sys.argv[1], run_name="bridge_probe")
except ImportError:
    pass
for name in ("pydantic", "pydantic_core", "copilot"):
    print(name, importlib.util.find_spec(name).origin)
if sys.platform == "win32":
    import copilot, pydantic
    print(pydantic.__file__, copilot.__file__)
"""


def test_worker_imports_from_release_lib(built: tuple[Path, Path]) -> None:
    _, release = built
    ran = subprocess.run(
        [sys.executable, "-I", "-B", "-X", "utf8", "-c", PROBE, str(release / "engine/bridge.py")],
        env={},
        check=False,
        capture_output=True,
        text=True,
    )
    assert ran.returncode == 0, ran.stderr
    origins = dict(line.split(" ", 1) for line in ran.stdout.splitlines()[:3])
    assert set(origins) == {"pydantic", "pydantic_core", "copilot"}
    for name, origin in origins.items():
        assert Path(origin).resolve().is_relative_to((release / "lib").resolve()), (name, origin)


MANIFEST_PROBE = """
import runpy, sys
try:
    runpy.run_path(sys.argv[1], run_name="bridge_probe")
except ImportError:
    if "library_manifest" not in sys.modules:
        raise
import library_manifest
print(library_manifest.__file__)
"""


def test_packaged_bridge_imports_library_manifest(built: tuple[Path, Path], tmp_path: Path) -> None:
    """The release lib holds Windows wheels that do not load here, so the engine is copied
    beside no lib and resolves pydantic from this environment; the engine files are the release's.
    A bridge import that fails before `library_manifest` is bound fails the test."""
    _, release = built
    engine = tmp_path / "engine"
    shutil.copytree(release / "engine", engine)
    ran = subprocess.run(
        [sys.executable, "-I", "-B", "-X", "utf8", "-c", MANIFEST_PROBE, str(engine / "bridge.py")],
        env={},
        check=False,
        capture_output=True,
        text=True,
    )
    assert ran.returncode == 0, ran.stderr
    assert Path(ran.stdout.strip()).resolve() == (engine / "library_manifest.py").resolve()


GOOD = b"wheel-bytes"
GOOD_SHA = hashlib.sha256(GOOD).hexdigest()
URL = "https://files.pythonhosted.org/x/foo-1.0-%s.whl"
NONE_ANY = "py3-none-any"


class Served(io.BytesIO):
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


@pytest.fixture
def runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """runtime.py in a fresh module, rooted in tmp_path, with no network and a fake export."""
    spec = importlib.util.spec_from_file_location("credit_os_runtime_t", PACKAGING / "runtime.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "CACHE", tmp_path / "cache")
    return module


def arrange(
    runtime: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tag: str,
    export_hashes: set[str],
    body: bytes = GOOD,
) -> None:
    row = f'{{ url = "{URL % tag}", hash = "sha256:{GOOD_SHA}" }}'
    lock = f'[[package]]\nname = "foo"\nversion = "1.0"\nwheels = [\n{row}\n]\n'
    (runtime.ROOT / "uv.lock").write_text(lock)
    monkeypatch.setattr(runtime, "exported", lambda: {"foo": ("1.0", export_hashes)})
    monkeypatch.setattr(runtime.urllib.request, "urlopen", lambda url, timeout=0: Served(body))


def fetch_all(runtime: ModuleType) -> None:
    for url, sha, name in runtime.pinned_wheels():
        runtime.download(url, sha, name)


@pytest.mark.parametrize(
    ("tag", "export_hashes"),
    [
        (NONE_ANY, {"0" * 64}),
        (NONE_ANY, set()),
        ("cp312-cp312-win_amd64", {GOOD_SHA}),
        ("cp313-cp313-win32", {GOOD_SHA}),
        ("cp313-cp313t-win_amd64", {GOOD_SHA}),
        ("cp313-cp313-manylinux_2_17_x86_64", {GOOD_SHA}),
    ],
)
def test_wheel_choice_fails_closed(
    runtime: ModuleType, monkeypatch: pytest.MonkeyPatch, tag: str, export_hashes: set[str]
) -> None:
    arrange(runtime, monkeypatch, tag, export_hashes)
    with pytest.raises(ValueError):
        fetch_all(runtime)


def test_served_bytes_must_match_the_lock_hash(
    runtime: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    arrange(runtime, monkeypatch, NONE_ANY, {GOOD_SHA}, body=b"evil")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        fetch_all(runtime)
    assert not (runtime.CACHE / f"foo-1.0-{NONE_ANY}.whl").exists()


def test_tampered_cache_is_not_trusted(
    runtime: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    arrange(runtime, monkeypatch, NONE_ANY, {GOOD_SHA}, body=b"evil")
    runtime.CACHE.mkdir()
    (runtime.CACHE / f"foo-1.0-{NONE_ANY}.whl").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        fetch_all(runtime)


def test_genuine_bytes_are_cached(runtime: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    arrange(runtime, monkeypatch, "cp313-cp313-win_amd64", {GOOD_SHA})
    ((url, sha, name),) = runtime.pinned_wheels()
    assert runtime.download(url, sha, name).read_bytes() == GOOD
