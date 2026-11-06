"""One command for the issuer library's validation gates. Provider keys are removed: no gate pays.

    python3 apps/issuer-library/validate.py quick | full | browser | suite

Needs FW_PYTHON (the project's Python) and ISSUER_LIBRARY_JSDOM (jsdom, test-only); browser also
needs FW_PLAYWRIGHT_PYTHON (a Python with Playwright, test-only). Prints PASS|FAIL per gate and
exits non-zero on any failure.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parent
ROOT = APP.parents[1]
KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY")
NODE_TESTS = (
    "designs/design.test.cjs",
    "web/new-run.test.cjs",
    "web/context-embed.test.cjs",
    "web/report-renderer.test.cjs",
)
PYTHON_TESTS = (
    "tests/test_issuer_library_store.py",
    "tests/test_cpos_app.py",
    "tests/test_cpos_launch.py",
    "tests/test_reader_summary.py",
    "tests/test_cpos_handoffs.py",
    "tests/test_cpos_comparison.py",
    "tests/test_markdown_delivery.py",
    "tests/test_pathway_handoff_charts.py",
)
PYTEST = ("-m", "pytest", "-q", "-p", "no:cacheprovider", "-m", "not live and not browser")


def clean_env(**extra):
    env = {name: value for name, value in os.environ.items() if name not in KEYS}
    path = f"/usr/local/go/bin{os.pathsep}{env['PATH']}"
    return env | {"PATH": path, "PYTHONDONTWRITEBYTECODE": "1"} | extra


def required(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"FAIL {name} is not set")
    return value


def report(name, passed, output=""):
    counted = re.findall(r"\d+ passed[^\n]*|(?<=ℹ )pass \d+", output) if passed else ()
    print(("PASS " if passed else "FAIL ") + name, *(f"({c})" for c in counted[-1:]), flush=True)
    if not passed:
        print("\n".join(output.splitlines()[-40:]), flush=True)
    return passed


def gate(name, command, cwd=ROOT, **extra):
    done = subprocess.run(
        command,
        cwd=cwd,
        env=clean_env(**extra),
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return report(name, done.returncode == 0, done.stdout + done.stderr)


def retained():
    """Retained runs and deliverables never change; the live proof's new folder is the one exception."""
    done = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            "runs",
            "deliverables",
            ":(exclude)runs/cpos-reader-live-*",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return report("retained", done.returncode == 0 and not done.stdout.strip(), done.stdout)


def quick():
    results = [
        retained(),
        gate("fixture", [sys.executable, "-B", "designs/build.py"], cwd=APP),
        gate(
            "node",
            ["node", "--test", "--test-timeout=60000", *NODE_TESTS],
            cwd=APP,
            ISSUER_LIBRARY_JSDOM=required("ISSUER_LIBRARY_JSDOM"),
        ),
        gate("python", [required("FW_PYTHON"), *PYTEST, *PYTHON_TESTS]),
    ]
    return all(results)


def changed_python():
    commands = (
        ["git", "diff", "--name-only", "--diff-filter=d", "origin/main...HEAD", "--", "*.py"],
        ["git", "ls-files", "--modified", "--others", "--exclude-standard", "--", "*.py"],
    )
    names = set()
    for command in commands:
        names |= set(
            subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.split()
        )
    return sorted(name for name in names if (ROOT / name).exists())


def full():
    results = [quick()]
    windows = {"GOOS": "windows", "GOARCH": "amd64"}
    with tempfile.TemporaryDirectory() as temporary:
        for name, command, extra in [
            ("go test", ["go", "test", "-race", "./..."], {}),
            ("go vet", ["go", "vet", "./..."], {}),
            ("go vet windows", ["go", "vet", "./..."], windows),
            (
                "go test compile windows",
                ["go", "test", "-c", "-o", f"{temporary}/t.exe", "."],
                windows,
            ),
            ("go build windows amd64", ["go", "build", "-o", f"{temporary}/a.exe", "."], windows),
            (
                "go build windows arm64",
                ["go", "build", "-o", f"{temporary}/b.exe", "."],
                windows | {"GOARCH": "arm64"},
            ),
        ]:
            results.append(gate(name, command, cwd=APP, **extra))
    ruff = Path(required("FW_PYTHON")).parent / "ruff"
    changed = changed_python()
    results.append(
        gate("ruff", [str(ruff), "check", *changed]) if changed else report("ruff", True)
    )
    return all(results)


def browser():
    with tempfile.TemporaryDirectory() as temporary:
        binary = f"{temporary}/issuer-library"
        if not gate("go build", ["go", "build", "-o", binary, "."], cwd=APP):
            return False
        return gate(
            "browser",
            [required("FW_PLAYWRIGHT_PYTHON"), "designs/browser_check.py", "chromium", "firefox"],
            cwd=APP,
            FW_PYTHON=required("FW_PYTHON"),
            ISSUER_LIBRARY_BINARY=binary,
        )


def suite(shards, root, known, out):
    """Every test outside tests/test_method_*, split by file. Passes when no failure is new."""
    listed = subprocess.run(
        ["git", "ls-files", "tests"], cwd=root, capture_output=True, text=True, check=True
    )
    files = sorted(
        name
        for name in listed.stdout.split()
        if re.search(r"(^|/)test_[^/]*\.py$", name) and not name.startswith("tests/test_method_")
    )
    out.mkdir(parents=True, exist_ok=True)
    running = []
    for number in range(shards):
        with (out / f"shard-{number}.out").open("w") as log:
            running.append(
                subprocess.Popen(
                    [
                        required("FW_PYTHON"),
                        *PYTEST,
                        "--continue-on-collection-errors",
                        "--tb=line",
                        "-rfE",
                        "-o",
                        "faulthandler_timeout=600",
                        "-o",
                        "pythonpath=src . tests",
                        *files[number::shards],
                    ],
                    cwd=root,
                    env=clean_env(),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                )
            )
    # Pytest exits 0 or 1 only after running tests; anything else means they did not run.
    unrun = [number for number, process in enumerate(running) if process.wait() not in (0, 1)]
    lines = [
        line
        for number in range(shards)
        for line in (out / f"shard-{number}.out").read_text(errors="replace").splitlines()
    ]
    failures = sorted({line.split()[1] for line in lines if re.match(r"(FAILED|ERROR) \S", line)})
    (out / "failures.txt").write_text("".join(f"{name}\n" for name in failures))
    for line in lines:
        if re.search(r"\d+ (passed|failed|errors?).* in \d", line):
            print(line, flush=True)
    new = sorted(set(failures) - set(known.read_text().split() if known else ()))
    for number in unrun:
        print(f"Shard {number} did not run its tests; see {out}/shard-{number}.out", flush=True)
    return report(
        f"suite: {len(failures)} failures, {len(new)} new", not new and not unrun, "\n".join(new)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("quick", "full", "browser", "suite"))
    parser.add_argument("--shards", type=int, default=6)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--known", type=Path)
    parser.add_argument(
        "--out", type=Path, default=Path(tempfile.gettempdir()) / "issuer-library-suite"
    )
    arguments = parser.parse_args()
    if arguments.mode == "suite":
        passed = suite(arguments.shards, arguments.root, arguments.known, arguments.out)
    else:
        passed = {"quick": quick, "full": full, "browser": browser}[arguments.mode]()
    sys.exit(not passed)


if __name__ == "__main__":
    main()
