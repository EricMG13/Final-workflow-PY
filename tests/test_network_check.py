"""Network-path check package: the folder generator and the check script it writes."""

import importlib.util
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

PACKAGING = Path(__file__).resolve().parents[1] / "apps/issuer-library/packaging"

WHEELS = [
    "pydantic-2.14.1-py3-none-any.whl",
    "pydantic_core-2.50.1-cp313-cp313-win_amd64.whl",
    "annotated_types-0.8.0-py3-none-any.whl",
    "typing_extensions-4.16.0-py3-none-any.whl",
    "typing_inspection-0.4.4-py3-none-any.whl",
    "fastapi-0.162.0-py3-none-any.whl",
    "starlette-1.10.0-py3-none-any.whl",
    "annotated_doc-0.0.5-py3-none-any.whl",
    "uvicorn-0.54.0-py3-none-any.whl",
    "h11-0.16.0-py3-none-any.whl",
    "click-8.5.0-py3-none-any.whl",
    "anyio-4.16.0-py3-none-any.whl",
    "idna-3.20-py3-none-any.whl",
    "opentelemetry_api-1.45.2-py3-none-any.whl",
]


@pytest.fixture
def network_check() -> ModuleType:
    spec = importlib.util.spec_from_file_location("network_check", PACKAGING / "network_check.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_folder_has_no_executable_and_the_server_closure(
    network_check: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_download(url: str, sha: str, name: str) -> Path:
        calls.append((name, sha))
        wheel = tmp_path / "wheels" / name
        wheel.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(name.split("-")[0] + "/__init__.py", "")
        return wheel

    monkeypatch.setattr(network_check, "download", fake_download)
    target = tmp_path / "check"
    network_check.build(target)

    assert not [p for p in target.rglob("*") if p.suffix in {".exe", ".dll"}]
    assert (target / "lib/pydantic_core").is_dir()
    command = (target / "Check.cmd").read_bytes()
    assert b"C:\\Program Files\\Statestreet\\Python313\\pythonw.exe" in command
    assert b" -I -B -X utf8 " in command
    assert b"\r\n" in command and re.search(rb"(?<!\r)\n", command) is None
    assert [name for name, _ in calls] == WHEELS
    sha = dict(calls)["pydantic_core-2.50.1-cp313-cp313-win_amd64.whl"]
    assert sha == "7816e98acc08119dc0f340ab167048ecc54126316330c1f0caf7c6756c88e28f"


def test_check_script_serves_health_and_writes_pass(
    network_check: ModuleType, tmp_path: Path
) -> None:
    import pydantic_core

    target = tmp_path / "check"
    network_check.write_scripts(target)
    temp = tmp_path / "temp"
    temp.mkdir()
    done = subprocess.run(
        [sys.executable, "-I", "-B", "-X", "utf8", str(target / "check.py")],
        env={"TEMP": str(temp)},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    lines = (temp / "credit-os-network-check.txt").read_text(encoding="utf-8").splitlines()
    assert "PASS" in lines
    assert f"pydantic_core: {pydantic_core.__file__}" in lines
    for field in ("import_ms", "first_response_ms"):
        assert any(re.fullmatch(field + r": \d+", line) for line in lines), lines
