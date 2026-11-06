"""Build the offline Windows packages: pinned runtime, engine, front end, launcher. Never run providers."""

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from runtime import bundle, clear

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
OUTPUT = ROOT / "artifacts/issuer-library"
CHECKS = [
    "tests/test_issuer_library_discovery.py",
    "tests/test_issuer_library_server.py",
    "tests/test_issuer_library_jobs.py",
    "tests/test_issuer_library_store.py",
]
subprocess.run([sys.executable, str(APP / "packaging/sync_assets.py")], check=True)
subprocess.run([sys.executable, "-m", "pytest", "-q", *CHECKS], cwd=ROOT, check=True)
for architecture in ["amd64", "arm64"]:
    target = OUTPUT / f"windows-{architecture}"
    target.mkdir(parents=True, exist_ok=True)
    # A file an earlier build shipped must not reach this zip; bundle keeps the pinned runtime.
    clear(target, {"engine"})
    bundle(target, architecture)
    shutil.copyfile(APP / "README.md", target / "README.md")
    shutil.copyfile(APP / "web/fonts/OFL.txt", target / "FONT-LICENSE.txt")
    shutil.copyfile(APP / "web/icons/LICENSE", target / "ICON-LICENSE.txt")
    for document in ["DESIGN.md", "DESIGN-SOURCES.md"]:
        shutil.copyfile(APP / document, target / document)
    shutil.copyfile(APP / "run-manifest.example.json", target / "run-manifest.example.json")
    archive = OUTPUT / f"Issuer-Library-{architecture}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as archive_handle:
        for file in sorted(target.rglob("*")):
            if file.is_file():
                archive_handle.write(file, file.relative_to(target))
    print(archive)
    print(
        f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name} (windows/{architecture})"
    )
