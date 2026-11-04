"""Pins and reference integrity for the shared CP-1 chain case."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp1-chain"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_cp1_chain_case_files_are_shared_pinned() -> None:
    case_paths = sorted(
        path.relative_to(ROOT).as_posix()
        for pattern in (CASE.glob("*.json"), (CASE / "fixtures").glob("*.txt"))
        for path in pattern
    )
    assert len(case_paths) == 12

    pins = json.loads((ROOT / "cases" / "PINS.json").read_text(encoding="utf-8"))
    pinned_case_paths = {path for path in pins if path.startswith("cases/cp1-chain/")}
    assert pinned_case_paths == set(case_paths)
    assert all(pins[path] == _sha256(ROOT / path) for path in case_paths)

    manifest = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
    reference_path = CASE / manifest["reference_file"]
    assert _sha256(reference_path) == manifest["reference_sha256"]
