"""The full test suite in shards, for the nightly run. Standard library only.

    python tools/nightly_tests.py run --shard 0 --shards 16 --out out
    python tools/nightly_tests.py report --shards 16 --known tests/nightly-known-failures.txt out

``run`` collects every test file in each shard and keeps every n-th test (the pytest hook in
``tools/nightly_shard.py``), so slow tests spread evenly. It runs pytest with the ``live`` and
``browser`` markers excluded and provider keys removed, and writes
``shard-<n>.log`` and ``shard-<n>.exit``, then prints the log's last lines (the failure summary,
or a crash's trace) to the job log. ``report`` collects every FAILED and ERROR node id from
the logs, compares them with the known list and prints a Markdown summary (also appended to
``$GITHUB_STEP_SUMMARY`` when set). It exits 1 when a failure is not on the known list or a shard
did not finish its tests, so a red run means something new broke.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "COPILOT_GITHUB_TOKEN",
    "GH_TOKEN",
    "GITHUB_TOKEN",
)
TEST_FILE = re.compile(r"(^|/)test_[^/]*\.py$")
OUTCOME = re.compile(r"^(FAILED|ERROR) (\S+)")
SUMMARY = re.compile(r"\d+ (passed|failed|errors?|skipped).* in [\d.]+s")
RAN = {"0", "1"}  # pytest exits 0 or 1 only after it ran the tests
SHARD_ENV = "NIGHTLY_SHARD"  # "<shard>/<shards>", read by tools/nightly_shard.py
TAIL = 400  # log lines printed to the job log: -rfE lists every failure at the end


def test_files(root: Path) -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "tests"], cwd=root, capture_output=True, text=True, check=True
    )
    return sorted(name for name in listed.stdout.split() if TEST_FILE.search(name))


def pytest_command(python: str, files: list[str]) -> list[str]:
    return [
        python,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "tools.nightly_shard",
        "--durations=30",
        "-m",
        "not live and not browser",
        "--continue-on-collection-errors",
        "--tb=line",
        "-rfE",
        "-o",
        "faulthandler_timeout=900",
        "-o",
        "tmp_path_retention_policy=failed",  # a passing test's tmp_path goes; stores fill disks
        "-o",
        "pythonpath=src . tests",
        *files,
    ]


def run_shard(root: Path, shard: int, shards: int, out: Path, minutes: float) -> str:
    env = {name: value for name, value in os.environ.items() if name not in KEYS}
    out.mkdir(parents=True, exist_ok=True)
    with (out / f"shard-{shard}.log").open("w") as log:
        print(f"shard {shard}/{shards}", file=log, flush=True)
        try:
            done = subprocess.run(
                pytest_command(sys.executable, test_files(root)),
                cwd=root,
                env=env | {"PYTHONDONTWRITEBYTECODE": "1", SHARD_ENV: f"{shard}/{shards}"},
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                timeout=minutes * 60,
                check=False,
            )
            status = str(done.returncode)
        except subprocess.TimeoutExpired:
            status = "timeout"
    (out / f"shard-{shard}.exit").write_text(status)
    return status


@dataclass
class Results:
    failures: set[str] = field(default_factory=set)
    summaries: dict[int, str] = field(default_factory=dict)
    statuses: dict[int, str] = field(default_factory=dict)


def read_results(folder: Path) -> Results:
    results = Results()
    for exit_file in sorted(folder.rglob("shard-*.exit")):
        shard = int(exit_file.stem.split("-")[1])
        results.statuses[shard] = exit_file.read_text().strip()
        log = exit_file.with_suffix(".log")
        text = log.read_text(errors="replace") if log.exists() else ""
        for line in text.splitlines():
            match = OUTCOME.match(line)
            if match is not None:
                results.failures.add(match[2])
            elif SUMMARY.search(line):
                results.summaries[shard] = line.strip("= ")
    return results


def known_failures(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    lines = (line.split("#", 1)[0].strip() for line in path.read_text().splitlines())
    return {line for line in lines if line}


def report(results: Results, known: set[str], shards: int) -> tuple[str, bool]:
    unfinished = [n for n in range(shards) if results.statuses.get(n) not in RAN]
    new = sorted(results.failures - known)
    fixed = sorted(known - results.failures)
    lines = [
        "## Nightly full test suite",
        "",
        (
            f"{len(results.failures)} failing, {len(new)} new, {len(fixed)} known now passing, "
            f"{len(unfinished)} shard(s) unfinished."
        ),
        "",
        "| Shard | Exit | Result |",
        "|---|---|---|",
    ]
    for shard in range(shards):
        status = results.statuses.get(shard, "missing")
        lines.append(f"| {shard} | {status} | {results.summaries.get(shard, '-')} |")
    for title, names in (("New failures", new), ("Known failures now passing", fixed)):
        if names:
            lines += ["", f"### {title}", "", *(f"- `{name}`" for name in names)]
    return "\n".join(lines) + "\n", not new and not unfinished


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--shard", type=int, required=True)
    run.add_argument("--shards", type=int, required=True)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--minutes", type=float, default=300)
    summary = commands.add_parser("report")
    summary.add_argument("--shards", type=int, required=True)
    summary.add_argument("--known", type=Path)
    summary.add_argument("folder", type=Path)
    arguments = parser.parse_args(argv)
    if arguments.command == "run":
        status = run_shard(
            ROOT, arguments.shard, arguments.shards, arguments.out, arguments.minutes
        )
        log = arguments.out / f"shard-{arguments.shard}.log"
        print(*log.read_text(errors="replace").splitlines()[-TAIL:], sep="\n")
        print(f"shard {arguments.shard}: pytest exit {status}")
        return 0 if status in RAN else 1
    text, passed = report(
        read_results(arguments.folder), known_failures(arguments.known), arguments.shards
    )
    print(text)
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as handle:
            handle.write(text)
    failing = sorted(read_results(arguments.folder).failures)
    (arguments.folder / "failures.txt").write_text("".join(f"{name}\n" for name in failing))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
