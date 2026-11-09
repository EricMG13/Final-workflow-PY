"""Build the Credit OS network-share package: wheels, engine, front end, launcher. No providers."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import unpack

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
CHECKS = [
    "tests/test_issuer_library_discovery.py",
    "tests/test_issuer_library_server.py",
    "tests/test_issuer_library_jobs.py",
    "tests/test_issuer_library_store.py",
]
PYTHON = r"C:\Program Files\Statestreet\Python313\pythonw.exe"
EXAMPLE = {"workspace": r"\\server\share\CreditOS\workspace"}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def launcher(version: str) -> str:
    # goto, not a ( ) block, so a parenthesis in a share path cannot break it.
    start = f'"{PYTHON}" -I -B -X utf8 "%~dp0app\\{version}\\start.py"'
    return "\r\n".join(
        [
            "@echo off",
            f"call :run {start} %*",
            "exit /b %ERRORLEVEL%",
            ":run",
            "if exist %1 goto python",
            "echo Credit OS needs the company Python at %~1, which is not on this PC.",
            "pause",
            "exit /b 1",
            ":python",
            "if exist %6 goto release",
            "echo This Credit OS release is missing: %~6",
            "pause",
            "exit /b 1",
            ":release",
            'start "Credit OS" %*',
            "",
        ]
    )


def build(target: Path) -> Path:
    version = (
        git("show", "-s", "--format=%cd", "--date=format:%Y.%m.%d", "HEAD")
        + "-"
        + git("rev-parse", "HEAD")[:12]
    )
    release = target / "app" / version
    if release.exists():
        shutil.rmtree(release)
    engine = release / "engine"
    engine.mkdir(parents=True)
    unpack(release / "lib")
    skip = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in ["bridge.py", "store.py", "catalog.json"]:
        shutil.copyfile(APP / "engine" / name, engine / name)
    shutil.copyfile(ROOT / "cases/context/research-minimal.json", engine / "smoke-context.json")
    (engine / "VERSION").write_text(version, encoding="utf-8")
    shutil.copytree(ROOT / "src", engine / "src", ignore=skip)
    # The launcher reads each module's method from these, relative to the engine folder.
    for name in ["docs/reuse/selected-methods", "docs/visualisations", "prompts"]:
        shutil.copytree(ROOT / name, engine / name, ignore=skip)
    shutil.copytree(APP / "web", release / "web")  # beside the engine, as the server finds it
    for source, name in [
        ("packaging/start.py", "start.py"),
        ("packaging/Smoke-test.ps1", "Smoke-test.ps1"),
        ("README.md", "README.md"),
        ("web/fonts/OFL.txt", "FONT-LICENSE.txt"),
        ("web/icons/LICENSE", "ICON-LICENSE.txt"),
        ("DESIGN.md", "DESIGN.md"),
        ("DESIGN-SOURCES.md", "DESIGN-SOURCES.md"),
        ("run-manifest.example.json", "run-manifest.example.json"),
    ]:
        shutil.copyfile(APP / source, release / name)
    (target / "Credit OS.cmd").write_bytes(launcher(version).encode("ascii"))
    (target / "default-workspace.json.example").write_text(
        json.dumps(EXAMPLE) + "\n", encoding="utf-8"
    )
    binaries = [p for p in target.rglob("*") if p.suffix.lower() in {".exe", ".dll"}]
    if binaries:
        raise ValueError(f"The package must hold no executable: {binaries[0]}")
    return release


if __name__ == "__main__":
    subprocess.run([sys.executable, str(APP / "packaging/sync_assets.py")], check=True)
    subprocess.run([sys.executable, "-m", "pytest", "-q", *CHECKS], cwd=ROOT, check=True)
    print(build(ROOT / "artifacts/issuer-library/CreditOS"))
