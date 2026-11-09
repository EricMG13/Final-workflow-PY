"""The nightly runner splits the suite deterministically and fails only on new failures."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tools import nightly_tests as nightly

ROOT = Path(__file__).resolve().parents[1]
SLOW = "import time\n\n" + "".join(f"def test_{n}():\n    time.sleep(0)\n\n" for n in range(7))


def _ran(folder: Path, shard: int, shards: int) -> list[str]:
    """Node ids the real plugin keeps for one shard, from pytest's own verbose report."""
    command = [*nightly.pytest_command(sys.executable, ["test_slow.py", "test_fast.py"]), "-rA"]
    done = subprocess.run(
        command,
        cwd=folder,
        env=os.environ | {nightly.SHARD_ENV: f"{shard}/{shards}", "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    return re.findall(r"^PASSED (\S+)", done.stdout, re.MULTILINE)


def test_shards_split_tests_not_files_so_a_slow_file_is_spread(tmp_path: Path) -> None:
    (tmp_path / "test_slow.py").write_text(SLOW)
    (tmp_path / "test_fast.py").write_text("def test_a():\n    pass\n")
    ran = [_ran(tmp_path, n, 3) for n in range(3)]
    everything = sorted(name for shard in ran for name in shard)
    assert everything == sorted(
        [*(f"test_slow.py::test_{n}" for n in range(7)), "test_fast.py::test_a"]
    )
    assert [len(shard) for shard in ran] == [3, 3, 2]
    assert all(any("test_slow.py" in name for name in shard) for shard in ran)


def _shard(folder: Path, n: int, status: str, log: str) -> None:
    (folder / f"shard-{n}.exit").write_text(status)
    (folder / f"shard-{n}.log").write_text(log)


LOG0 = (
    "shard 0/2: 3 files\n"
    "FAILED tests/test_x.py::test_one - AssertionError: 1 != 2\n"
    "ERROR tests/product/test_y.py - ModuleNotFoundError: No module named 'scripts'\n"
    "==== 2 failed, 10 passed, 1 error in 12.50s ====\n"
)
LOG1 = "shard 1/2: 2 files\n==== 7 passed in 3.00s ====\n"


def test_report_fails_only_on_a_failure_not_on_the_known_list(tmp_path: Path) -> None:
    _shard(tmp_path, 0, "1", LOG0)
    _shard(tmp_path, 1, "0", LOG1)
    results = nightly.read_results(tmp_path)
    assert results.failures == {"tests/test_x.py::test_one", "tests/product/test_y.py"}
    assert results.summaries == {
        0: "2 failed, 10 passed, 1 error in 12.50s",
        1: "7 passed in 3.00s",
    }
    text, passed = nightly.report(results, {"tests/product/test_y.py"}, 2)
    assert not passed and "- `tests/test_x.py::test_one`" in text
    text, passed = nightly.report(results, set(results.failures) | {"tests/gone.py::t"}, 2)
    assert passed and "### Known failures now passing" in text and "tests/gone.py::t" in text


@pytest.mark.parametrize("status", ["timeout", "2", "4"])
def test_a_shard_that_did_not_finish_fails_the_run(tmp_path: Path, status: str) -> None:
    _shard(tmp_path, 0, "0", LOG1)
    _shard(tmp_path, 1, status, "shard 1/2: 2 files\n")
    text, passed = nightly.report(nightly.read_results(tmp_path), set(), 2)
    assert not passed and "1 shard(s) unfinished" in text


def test_a_missing_shard_fails_the_run(tmp_path: Path) -> None:
    _shard(tmp_path, 0, "0", LOG1)
    text, passed = nightly.report(nightly.read_results(tmp_path), set(), 2)
    assert not passed and "| 1 | missing | - |" in text


def test_known_list_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    known = tmp_path / "known.txt"
    known.write_text("# header\n\ntests/a.py::t  # why\ntests/b.py\n")
    assert nightly.known_failures(known) == {"tests/a.py::t", "tests/b.py"}
    assert nightly.known_failures(tmp_path / "absent.txt") == set()


def test_command_excludes_paid_and_browser_tests_and_keeps_going() -> None:
    command = nightly.pytest_command("python", ["tests/a.py"])
    assert command[command.index("-m", 3) + 1] == "not live and not browser"
    assert "--continue-on-collection-errors" in command and command[-1] == "tests/a.py"
    assert "tmp_path_retention_policy=failed" in command


def test_run_prints_the_log_tail_to_the_job_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake(root: Path, shard: int, shards: int, out: Path, minutes: float) -> str:
        _shard(out, shard, "-11", "".join(f"line {n}\n" for n in range(nightly.TAIL + 5)))
        return "-11"

    monkeypatch.setattr(nightly, "run_shard", fake)
    code = nightly.main(["run", "--shard", "3", "--shards", "8", "--out", str(tmp_path)])
    printed = capsys.readouterr().out.splitlines()
    assert code == 1 and printed[-1] == "shard 3: pytest exit -11"
    assert printed[:-1] == [f"line {n}" for n in range(5, nightly.TAIL + 5)]
