"""The quality gate checks changed code only: changed lines, the functions they fall in,
and new files whole. Legacy findings elsewhere in a changed file are out of scope."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools import quality_gate as gate

LONG = "x = '" + "a" * 100 + "'\n"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _repo(tmp_path: Path, base_source: str) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "mod.py").write_text(base_source, encoding="utf-8")
    _git(root, "add", "mod.py")
    _git(root, "commit", "-q", "-m", "base")
    return root


BASE = (
    "def untouched() -> int:\n"
    "    " + LONG + "    return 1\n"
    "\n"
    "\n"
    "def touched() -> int:\n"
    "    return 2\n"
)


def test_hunk_lines_reads_both_sides_and_anchors_deletions() -> None:
    diff = "@@ -3,2 +3,0 @@ ctx\n-a\n-b\n@@ -10 +9,3 @@\n-c\n+d\n+e\n+f\n@@ -0,0 +1 @@\n+g\n"
    assert gate.hunk_lines(diff, side=1) == {3, 4, 10, 1}
    assert gate.hunk_lines(diff, side=3) == {3, 9, 10, 11, 1}


def test_function_spans_include_decorators_and_nested_functions() -> None:
    source = (
        "import functools\n\n@functools.cache\ndef f():\n    def g():\n        pass\n    return g\n"
    )
    assert sorted(gate.function_spans(source)) == [(3, 7), (5, 6)]


def test_owned_lines_expand_to_the_touched_function_only() -> None:
    owned = gate.owned_lines(BASE, {7})
    assert owned == {6, 7}
    assert gate.owned_lines(BASE, None) == set(range(1, BASE.count("\n") + 2))


def test_changed_lines_against_base(tmp_path: Path) -> None:
    root = _repo(tmp_path, BASE)
    (root / "mod.py").write_text(BASE.replace("return 2", "return 3"), encoding="utf-8")
    (root / "new.py").write_text("y = 1\n", encoding="utf-8")
    assert gate.changed_files(root, "HEAD") == ["mod.py", "new.py"]
    assert gate.changed_lines(root, "HEAD", "mod.py") == {7}
    assert gate.changed_lines(root, "HEAD", "new.py") is None


@pytest.mark.skipif(sys.platform == "win32", reason="git and tool paths are POSIX here")
def test_gate_reports_findings_in_changed_code_only(tmp_path: Path) -> None:
    root = _repo(tmp_path, BASE)
    added = "    " + LONG + "    z: int = 'no'\n    return 2\n"
    edited = BASE.replace("    return 2\n", added)
    (root / "mod.py").write_text(edited, encoding="utf-8")
    (root / "new.py").write_text("def  spaced( ) -> int:\n    return 1\n", encoding="utf-8")
    result = gate.run_gate(root, "HEAD")
    assert result.files == ["mod.py", "new.py"]
    seen = {(f.path, f.line, f.tool, f.code) for f in result.findings}
    assert ("mod.py", 7, "ruff", "E501") in seen, result.findings
    assert ("mod.py", 8, "mypy", "assignment") in seen, result.findings
    assert ("new.py", 1, "format", "FMT") in seen, result.findings
    assert not [f for f in result.findings if f.path == "mod.py" and f.line == 2], "legacy E501"


def test_gate_is_clean_when_nothing_changed(tmp_path: Path) -> None:
    root = _repo(tmp_path, BASE)
    result = gate.run_gate(root, "HEAD")
    assert result.files == [] and result.findings == [] and result.owned == 0


def test_main_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _repo(tmp_path, BASE)
    assert gate.main(["--root", str(root), "--base", "HEAD"]) == 0
    assert "0 finding(s) in 0 changed file(s)" in capsys.readouterr().out
    assert gate.main(["--root", str(root), "--base", "no-such-ref"]) == 2
    assert "could not run" in capsys.readouterr().err


@pytest.mark.skipif(sys.platform == "win32", reason="git and tool paths are POSIX here")
def test_two_changed_files_with_one_module_name_are_typed_one_by_one(tmp_path: Path) -> None:
    """mypy stops with exit 2 on two `build.py` files; the gate checks each file alone."""
    root = _repo(tmp_path, BASE)
    for case in ("a", "b"):
        (root / case / "builder").mkdir(parents=True)
    (root / "a" / "builder" / "build.py").write_text("x: int = 1\n", encoding="utf-8")
    (root / "b" / "builder" / "build.py").write_text('y: int = "no"\n', encoding="utf-8")
    result = gate.run_gate(root, "HEAD")
    assert result.files == ["a/builder/build.py", "b/builder/build.py"]
    seen = {(f.path, f.line, f.tool, f.code) for f in result.findings}
    assert seen == {("b/builder/build.py", 1, "mypy", "assignment")}, result.findings


@pytest.mark.skipif(sys.platform == "win32", reason="git and tool paths are POSIX here")
def test_gate_flags_a_stale_noqa_for_a_gate_only_code(tmp_path: Path) -> None:
    root = _repo(tmp_path, BASE)
    (root / "new.py").write_text(
        "def few(a: int) -> int:  # noqa: PLR0913\n    return a\n", encoding="utf-8"
    )
    result = gate.run_gate(root, "HEAD")
    seen = {(f.path, f.line, f.tool, f.code) for f in result.findings}
    assert ("new.py", 1, "ruff", "RUF100") in seen, result.findings
