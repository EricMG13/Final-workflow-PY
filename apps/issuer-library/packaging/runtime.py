"""Unpack the locked Windows wheels into a release; verify every downloaded SHA-256."""

import hashlib
import re
import shutil
import subprocess
import tomllib
import urllib.request
import zipfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
CACHE = ROOT / "artifacts/issuer-library/runtime-cache"


def download(url: str, sha: str, name: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / name
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != sha:
        with urllib.request.urlopen(url, timeout=90) as response:
            raw = response.read(100 << 20)
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError(f"Checksum mismatch: {name}")
        target.write_bytes(raw)
    return target


def exported() -> dict[str, tuple[str, set[str]]]:
    """{name: (version, {sha256})} from the lock, as `uv export` lists the runtime closure."""
    text = subprocess.run(
        [
            "uv",
            "export",
            "--locked",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--no-header",
            "--no-annotate",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    found = {}
    for block in re.split(r"\n(?=\S)", text.replace(" \\\n", "\n ")):
        head = re.match(r"([A-Za-z0-9._-]+)==(\S+)", block)
        if head:
            found[head[1].lower().replace("_", "-")] = (
                head[2],
                set(re.findall(r"--hash=sha256:([0-9a-f]{64})", block)),
            )
    return found


def pinned_wheels() -> list[tuple[str, str, str]]:
    """(url, sha256, filename) per exported package: its one none-any or cp313 win_amd64 wheel."""
    lock = {
        p["name"]: p
        for p in tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))["package"]
    }
    chosen = []
    for name, (version, hashes) in exported().items():
        entry = lock.get(name)
        if entry is None or entry["version"] != version:
            raise ValueError(f"No unique pinned Windows wheel: {name}")
        matches = [
            (w["url"], w["hash"].removeprefix("sha256:"), w["url"].rsplit("/", 1)[1])
            for w in entry.get("wheels", [])
            if w["url"].endswith("-none-any.whl")
            or (
                "-cp313-" in w["url"]
                and w["url"].endswith("-win_amd64.whl")
                and "-cp313t-" not in w["url"]
            )
        ]
        if len(matches) != 1:
            raise ValueError(f"No unique pinned Windows wheel: {name}")
        if matches[0][1] not in hashes:
            raise ValueError(f"Wheel hash is not in the export: {name}")
        chosen.append(matches[0])
    return chosen


def unpack(lib: Path) -> None:
    if lib.exists():
        shutil.rmtree(lib)
    lib.mkdir(parents=True)
    for url, sha, filename in pinned_wheels():
        with zipfile.ZipFile(download(url, sha, filename)) as archive:
            archive.extractall(lib)
