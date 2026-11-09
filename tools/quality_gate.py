"""Quality gate for changed Python code: readability, maintainability, complexity, types.

    uv run python tools/quality_gate.py [--base origin/main] [--json]

Compares the working tree with ``--base`` and checks only the code that changed:
every changed line, plus the whole body of every function a changed line falls in.
New files are checked whole. The checks are ``ruff check`` with the rules in
``tools/ruff-gate.toml``, ``ruff format``, and strict ``mypy`` (tests excluded from
mypy). A finding outside the changed code is not reported, so the gate holds new
work to the standard without a rewrite of the existing code. Exit status 1 when a
finding remains, 2 when the gate itself could not run. Standard library only.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_CONFIG = ROOT / "tools" / "ruff-gate.toml"
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
MYPY_LINE = re.compile(r"^(?P<path>[^:\n]+):(?P<line>\d+):(?:\d+:)? error: (?P<message>.*)$")
DUPLICATE_MODULE = ("Duplicate module named", "Source file found twice")


@dataclass(frozen=True)
class Finding:
    tool: str
    path: str
    line: int
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.tool} {self.code} {self.message}"


class GateError(Exception):
    """The gate could not run (bad base ref, tool missing)."""


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    except OSError as error:
        raise GateError(f"cannot run {command[0]}: {error}") from error


def git(root: Path, *args: str) -> str:
    done = _run(["git", *args], root)
    if done.returncode != 0:
        raise GateError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout


def changed_files(root: Path, base: str) -> list[str]:
    """Python files that differ from ``base`` in the working tree, plus untracked ones."""
    tracked = git(root, "diff", "--name-only", "--diff-filter=ACMR", base, "--", "*.py")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "--", "*.py")
    names = set(tracked.split()) | set(untracked.split())
    return sorted(name for name in names if (root / name).is_file())


def hunk_lines(diff: str, side: int) -> set[int]:
    """Line numbers a unified diff touches on one side (1 = old, 3 = new).

    A pure deletion or insertion marks the line it sits next to on that side, so a
    function that only lost lines still counts as touched.
    """
    lines: set[int] = set()
    for header in diff.splitlines():
        match = HUNK.match(header)
        if match is None:
            continue
        start = int(match[side])
        count = 1 if match[side + 1] is None else int(match[side + 1])
        lines.update(range(start, start + count) if count else {max(start, 1)})
    return lines


def changed_lines(root: Path, base: str, path: str) -> set[int] | None:
    """New-side line numbers that differ from ``base``; ``None`` means the whole file."""
    if not git(root, "ls-files", "--", path).strip():
        return None
    return hunk_lines(git(root, "diff", "-U0", base, "--", path), side=3)


def function_spans(source: str) -> list[tuple[int, int]]:
    """(first, last) line of every function and method, decorators included."""
    spans = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            first = min([node.lineno, *(d.lineno for d in node.decorator_list)])
            spans.append((first, node.end_lineno or node.lineno))
    return spans


def owned_lines(source: str, changed: set[int] | None) -> set[int]:
    """The changed lines plus every line of each function a changed line falls in."""
    total = source.count("\n") + 1
    if changed is None:
        return set(range(1, total + 1))
    owned = set(changed)
    for first, last in function_spans(source):
        if any(first <= line <= last for line in changed):
            owned.update(range(first, last + 1))
    return owned


def ruff_findings(root: Path, python: str, files: list[str]) -> list[Finding]:
    command = [python, "-m", "ruff", "check", "--config", str(GATE_CONFIG)]
    done = _run([*command, "--output-format", "json", "--exit-zero", *files], root)
    if done.returncode != 0:
        raise GateError(f"ruff check failed: {done.stderr.strip()}")
    return [
        Finding(
            "ruff",
            _relative(root, row["filename"]),
            row["location"]["row"],
            row.get("code") or "syntax",
            row["message"],
        )
        for row in json.loads(done.stdout)
    ]


def format_lines(root: Path, python: str, path: str) -> set[int]:
    """Current line numbers ``ruff format`` would change in ``path``."""
    command = [python, "-m", "ruff", "format", "--config", str(GATE_CONFIG), "--diff", path]
    done = _run(command, root)
    if done.returncode not in (0, 1):
        raise GateError(f"ruff format failed on {path}: {done.stderr.strip()}")
    lines: set[int] = set()
    current = 0  # 0 until the first hunk header; the file headers above it are skipped
    for text in done.stdout.splitlines():
        match = HUNK.match(text)
        if match is not None:
            current = int(match[1])
        elif current and text.startswith(("-", "+")):
            lines.add(current)
            current += text.startswith("-")
        elif current and text.startswith(" "):
            current += 1
    return lines


def _mypy_lines(root: Path, python: str, files: list[str]) -> str:
    command = [python, "-m", "mypy", "--follow-imports=silent", "--no-error-summary", *files]
    done = _run(command, root)
    # Two changed files with one module name (two builder/build.py) stop mypy with exit 2 before
    # it checks anything; each file is then checked on its own.
    if len(files) > 1 and any(text in done.stdout for text in DUPLICATE_MODULE):
        return "".join(_mypy_lines(root, python, [name]) for name in files)
    if done.returncode not in (0, 1):
        raise GateError(f"mypy failed: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def mypy_findings(root: Path, python: str, files: list[str]) -> list[Finding]:
    """Strict mypy errors in the non-test files; tests are typed by convention only."""
    sources = [name for name in files if not is_test(name)]
    if not sources:
        return []
    findings = []
    for text in _mypy_lines(root, python, sources).splitlines():
        match = MYPY_LINE.match(text)
        if match is not None:
            path, message = _relative(root, match["path"]), match["message"]
            code = message.rsplit("  [", 1)[1].rstrip("]") if "  [" in message else "error"
            findings.append(Finding("mypy", path, int(match["line"]), code, message))
    return findings


def is_test(path: str) -> bool:
    parts = Path(path).parts
    return parts[0] == "tests" or parts[-1].startswith(("test_", "conftest"))


def _relative(root: Path, name: str) -> str:
    path = Path(name)
    if path.is_absolute():
        return path.resolve().relative_to(root.resolve()).as_posix()
    return path.as_posix()


@dataclass(frozen=True)
class GateResult:
    files: list[str]
    owned: int
    findings: list[Finding]


def run_gate(root: Path, base: str, python: str = sys.executable) -> GateResult:
    """Every finding of every check that falls inside the changed code."""
    files = changed_files(root, base)
    owned = {}
    for name in files:
        source = (root / name).read_text(encoding="utf-8", errors="replace")
        owned[name] = owned_lines(source, changed_lines(root, base, name))
    findings = []
    if files:
        findings += ruff_findings(root, python, files)
        findings += mypy_findings(root, python, files)
        for name in files:
            for line in sorted(format_lines(root, python, name)):
                findings.append(Finding("format", name, line, "FMT", "ruff format would change"))
    kept = [f for f in findings if f.line in owned.get(f.path, set())]
    kept.sort(key=lambda f: (f.path, f.line, f.tool, f.code))
    return GateResult(files, sum(len(lines) for lines in owned.values()), kept)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("--base", default="origin/main", help="ref to compare with")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args(argv)
    try:
        result = run_gate(arguments.root, arguments.base)
    except GateError as error:
        print(f"quality gate could not run: {error}", file=sys.stderr)
        return 2
    if arguments.json:
        print(json.dumps({**asdict(result), "findings": [asdict(f) for f in result.findings]}))
    else:
        for finding in result.findings:
            print(finding)
        print(
            f"quality gate: {len(result.findings)} finding(s) in {len(result.files)} changed "
            f"file(s), {result.owned} line(s) in scope"
        )
    return 1 if result.findings else 0


if __name__ == "__main__":
    sys.exit(main())
