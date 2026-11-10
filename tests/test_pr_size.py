"""PR size and copy check: each test builds its own temporary git repo."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools import pr_size

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "pr_size.py"
IDENT = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
UNKNOWN_SHA = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture(autouse=True)
def isolated_git_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """The developer's own git config (hooks, signing, aliases) must not reach any test."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *IDENT, *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


def write(repo: Path, files: dict[str, bytes]) -> None:
    for name, data in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def commit(repo: Path, message: str, files: dict[str, bytes] | None = None) -> str:
    write(repo, files or {})
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def make_repo(tmp_path: Path, base_files: dict[str, bytes] | None = None) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    base = commit(repo, "base", {"README.md": b"base\n", **(base_files or {})})
    return repo, base


def make_source(repo: Path, files: dict[str, bytes], remove: tuple[str, ...] = ()) -> str:
    """Commit on a side branch (the 'source' repo state), then return to main."""
    git(repo, "checkout", "-b", "src")
    for name in remove:
        git(repo, "rm", "-q", name)
    sha = commit(repo, "source", files)
    git(repo, "checkout", "main")
    return sha


def listing_text(sha: str, *paths: str) -> bytes:
    return "".join([f"source {sha}\n", *[f"{p}\n" for p in paths]]).encode()


def lines(count: int) -> bytes:
    return b"".join(f"line {i}\n".encode() for i in range(count))


def result(repo: Path, base: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--base", base],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )


def run(repo: Path, base: str) -> int:
    return result(repo, base).returncode


def test_identical_copy_is_not_counted(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    data = lines(900)
    sha = make_source(repo, {"vendor/big.txt": data})
    commit(
        repo,
        "copy",
        {"vendor/big.txt": data, "tools/copied-from.txt": listing_text(sha, "vendor/big.txt")},
    )
    listing = repo / "tools" / "copied-from.txt"
    assert pr_size.copied_mismatches(listing, repo) == []
    assert pr_size.pr_lines(base, repo) == 0
    assert run(repo, base) == 0


def test_edited_copy_is_a_mismatch(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    data = lines(50)
    sha = make_source(repo, {"vendor/f.txt": data})
    commit(
        repo,
        "copy",
        {
            "vendor/f.txt": data.replace(b"line 7\n", b"line 8\n"),
            "tools/copied-from.txt": listing_text(sha, "vendor/f.txt"),
        },
    )
    listing = repo / "tools" / "copied-from.txt"
    assert pr_size.copied_mismatches(listing, repo) == ["vendor/f.txt"]
    done = result(repo, base)
    assert done.returncode == 1
    assert "copy mismatch: vendor/f.txt" in done.stdout


def test_fixtures_and_lockfiles_are_not_counted(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    commit(
        repo,
        "excluded",
        {
            "tests/fixtures/a.txt": lines(100),
            "cases/x/b.txt": lines(100),
            "apps/issuer-library/web/testdata/c.txt": lines(100),
            "apps/issuer-library/designs/foo-answer-key.json": lines(100),
            "uv.lock": lines(100),
            "sub/uv.lock": lines(100),
        },
    )
    assert pr_size.pr_lines(base, repo) == 0
    assert run(repo, base) == 0


def test_801_counted_lines_fail(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    commit(repo, "800", {"src_new.txt": lines(800)})
    assert pr_size.pr_lines(base, repo) == 800
    assert run(repo, base) == 0
    commit(repo, "801", {"src_more.txt": lines(1)})
    assert pr_size.pr_lines(base, repo) == 801
    done = result(repo, base)
    assert done.returncode == 1
    assert "counted lines: 801 (limit 800)" in done.stdout


def test_deleted_upstream_path_matches_and_is_not_counted(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path, {"vendor/gone.txt": lines(300)})
    sha = make_source(repo, {}, remove=("vendor/gone.txt",))
    git(repo, "rm", "-q", "vendor/gone.txt")
    commit(repo, "delete", {"tools/copied-from.txt": listing_text(sha, "vendor/gone.txt")})
    listing = repo / "tools" / "copied-from.txt"
    assert pr_size.copied_mismatches(listing, repo) == []
    assert pr_size.pr_lines(base, repo) == 0
    assert run(repo, base) == 0


def test_listed_path_absent_at_source_but_present_is_a_mismatch(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    sha = make_source(repo, {"other.txt": b"x\n"})
    commit(
        repo,
        "extra",
        {"vendor/new.txt": b"x\n", "tools/copied-from.txt": listing_text(sha, "vendor/new.txt")},
    )
    listing = repo / "tools" / "copied-from.txt"
    assert pr_size.copied_mismatches(listing, repo) == ["vendor/new.txt"]
    done = result(repo, base)
    assert done.returncode == 1
    assert "copy mismatch: vendor/new.txt" in done.stdout


def test_unknown_source_sha_fails(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    commit(repo, "list", {"tools/copied-from.txt": listing_text(UNKNOWN_SHA, "vendor/x.txt")})
    done = result(repo, base)
    assert done.returncode == 1
    assert f"source commit {UNKNOWN_SHA} is not in this repository" in done.stderr


def replace_lines(data: bytes, count: int) -> bytes:
    """Return data with its first `count` lines replaced."""
    rows = data.splitlines(keepends=True)
    return b"".join([f"changed {i}\n".encode() for i in range(count)] + rows[count:])


def edited_setup(tmp_path: Path, replaced: int) -> tuple[Path, str]:
    """Source holds 900 lines; HEAD adds an edited copy absent at base (key scenarios 3 and 4).

    The setup used to put a different 1000-line file at base; under R-PRSIZE-1 that file would
    count against the merge base (key scenario 17), so these tests now use the absent-at-base case.
    """
    repo, base = make_repo(tmp_path)
    source_data = lines(900)
    sha = make_source(repo, {"vendor/big.txt": source_data})
    commit(
        repo,
        "copy and edit",
        {
            "vendor/big.txt": replace_lines(source_data, replaced),
            "tools/copied-from.txt": listing_text(sha, "edited vendor/big.txt"),
        },
    )
    return repo, base


def test_edited_copy_counts_only_its_difference_from_source(tmp_path: Path) -> None:
    repo, base = edited_setup(tmp_path, 3)
    assert pr_size.pr_lines(base, repo) == 6
    assert run(repo, base) == 0


def test_edited_path_is_not_a_mismatch(tmp_path: Path) -> None:
    repo, _ = edited_setup(tmp_path, 3)
    listing = repo / "tools" / "copied-from.txt"
    assert pr_size.copied_mismatches(listing, repo) == []


def test_edited_path_absent_at_source_is_a_mismatch(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    sha = make_source(repo, {"other.txt": b"x\n"})
    commit(
        repo,
        "new",
        {
            "new/file.py": b"x = 1\n",
            "tools/copied-from.txt": listing_text(sha, "edited new/file.py"),
        },
    )
    listing = repo / "tools" / "copied-from.txt"
    assert pr_size.copied_mismatches(listing, repo) == ["new/file.py"]
    done = result(repo, base)
    assert done.returncode == 1
    assert "copy mismatch: new/file.py" in done.stdout


def test_edited_path_absent_here_is_a_mismatch(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    sha = make_source(repo, {"vendor/f.txt": lines(5)})
    commit(repo, "list", {"tools/copied-from.txt": listing_text(sha, "edited vendor/f.txt")})
    listing = repo / "tools" / "copied-from.txt"
    assert pr_size.copied_mismatches(listing, repo) == ["vendor/f.txt"]
    assert run(repo, base) == 1


def test_edited_difference_over_800_fails(tmp_path: Path) -> None:
    repo, base = edited_setup(tmp_path, 401)
    assert pr_size.pr_lines(base, repo) == 802
    assert run(repo, base) == 1


def test_edited_path_binary_at_source_keeps_its_range_count(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    sha = make_source(repo, {"code.py": b"bin\x00ary\n"})
    commit(
        repo,
        "new text",
        {"code.py": lines(1000), "tools/copied-from.txt": listing_text(sha, "edited code.py")},
    )
    assert pr_size.pr_lines(base, repo) == 1000
    assert run(repo, base) == 1


def test_unknown_base_fails_with_a_message(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path)
    done = result(repo, "nonexistent-ref")
    assert done.returncode == 1
    assert "git failed" in done.stderr
    assert "nonexistent-ref" in done.stderr
    assert "Traceback" not in done.stderr


def test_dirty_working_tree_does_not_change_the_result(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    data = lines(900)
    sha = make_source(repo, {"vendor/big.txt": data})
    commit(
        repo,
        "copy",
        {"vendor/big.txt": data, "tools/copied-from.txt": listing_text(sha, "vendor/big.txt")},
    )
    write(repo, {"vendor/big.txt": b"dirty\n", "tools/copied-from.txt": listing_text(sha, "x.txt")})
    assert pr_size.copied_mismatches(repo / "tools" / "copied-from.txt", repo) == []
    assert pr_size.pr_lines(base, repo) == 0
    assert run(repo, base) == 0


def test_a_listed_directory_is_a_mismatch(tmp_path: Path) -> None:
    repo, base = make_repo(tmp_path)
    sha = make_source(repo, {"vendor/a.txt": b"a\n"})
    commit(
        repo, "copy", {"vendor/a.txt": b"a\n", "tools/copied-from.txt": listing_text(sha, "vendor")}
    )
    assert pr_size.copied_mismatches(repo / "tools" / "copied-from.txt", repo) == ["vendor"]
    assert run(repo, base) == 1


# Answer key tests/fixtures/pr-size/scenarios.json (sha256 01ac9082...e8), recipes and expected
# values copied verbatim except that stdout_contains is derived: "counted lines: N (limit 800)" then
# one "copy mismatch: <path>" per mismatch (checked against the key when this was embedded).
# Each expected entry is [counted, exit code, mismatches].
SCENARIOS = json.loads(
    r"""
[
{
 "id": 1,
 "name": "base-holds-drift-pr-adds-5",
 "base_commit": "base",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "base",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70], ["a", 0, 5]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  }
 ],
 "expected": [5, 0, []]
},
{
 "id": 2,
 "name": "same-pr-copies-and-edits-new-file-plus-appends-5",
 "base_commit": "base",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}, "vendor/g.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "base",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {
    "vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70], ["a", 0, 5]]},
    "vendor/g.txt": {"seq": [["e", 0, 10], ["s", 10, 90]]}
   },
   "listing": ["source $source", "edited vendor/f.txt", "edited vendor/g.txt"]
  }
 ],
 "expected": [25, 0, []]
},
{
 "id": 3,
 "name": "edited-copy-absent-at-base-small-drift",
 "base_commit": "root",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/g.txt": {"seq": [["s", 0, 900]]}}
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/g.txt": {"seq": [["c", 0, 3], ["s", 3, 897]]}},
   "listing": ["source $source", "edited vendor/g.txt"]
  }
 ],
 "expected": [6, 0, []]
},
{
 "id": 4,
 "name": "edited-copy-absent-at-base-drift-over-limit",
 "base_commit": "root",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/g.txt": {"seq": [["s", 0, 900]]}}
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/g.txt": {"seq": [["c", 0, 401], ["s", 401, 499]]}},
   "listing": ["source $source", "edited vendor/g.txt"]
  }
 ],
 "expected": [802, 1, []]
},
{
 "id": 5,
 "name": "edited-entry-byte-identical-to-source-absent-at-base",
 "base_commit": "root",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  }
 ],
 "expected": [0, 0, []]
},
{
 "id": 6,
 "name": "edited-entry-reverts-base-drift-to-source",
 "base_commit": "base",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "base",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  }
 ],
 "expected": [60, 0, []]
},
{
 "id": 7,
 "name": "plain-copy-at-base-becomes-edited",
 "base_commit": "base",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/h.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "base",
   "branch": "main",
   "files": {"vendor/h.txt": {"seq": [["s", 0, 100]]}},
   "listing": ["source $source", "vendor/h.txt"]
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/h.txt": {"seq": [["c", 0, 7], ["s", 7, 93]]}},
   "listing": ["source $source", "edited vendor/h.txt"]
  }
 ],
 "expected": [14, 0, []]
},
{
 "id": 8,
 "name": "plain-copy-matches-source",
 "base_commit": "root",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/big.txt": {"seq": [["s", 0, 900]]}}
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/big.txt": {"seq": [["s", 0, 900]]}},
   "listing": ["source $source", "vendor/big.txt"]
  }
 ],
 "expected": [0, 0, []]
},
{
 "id": 9,
 "name": "plain-copy-differs-from-source",
 "base_commit": "root",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 50]]}}
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 7], ["c", 0, 1], ["s", 8, 42]]}},
   "listing": ["source $source", "vendor/f.txt"]
  }
 ],
 "expected": [0, 1, ["vendor/f.txt"]]
},
{
 "id": 10,
 "name": "limit-edge-800-passes",
 "base_commit": "base",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "base",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70], ["a", 0, 800]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  }
 ],
 "expected": [800, 0, []]
},
{
 "id": 11,
 "name": "limit-edge-801-fails",
 "base_commit": "base",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "base",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70], ["a", 0, 801]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  }
 ],
 "expected": [801, 1, []]
},
{
 "id": 12,
 "name": "edited-file-deleted-listing-still-edited",
 "base_commit": "base",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "base",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70], ["x", 0, 5]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  },
  {
   "commit": "pr",
   "branch": "main",
   "remove": ["vendor/f.txt"],
   "listing": ["source $source", "edited vendor/f.txt"]
  }
 ],
 "expected": [105, 1, ["vendor/f.txt"]]
},
{
 "id": 13,
 "name": "edited-file-deleted-and-entry-removed",
 "base_commit": "base",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "base",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70], ["x", 0, 5]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  },
  {"commit": "pr", "branch": "main", "remove": ["vendor/f.txt"], "listing": ["source $source"]}
 ],
 "expected": [105, 0, []]
},
{
 "id": 14,
 "name": "edited-path-binary-at-source-text-at-head-absent-at-base",
 "base_commit": "root",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"code.py": {"hex": "62696e006172790a"}}
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"code.py": {"seq": [["t", 0, 1000]]}},
   "listing": ["source $source", "edited code.py"]
  }
 ],
 "expected": [1000, 1, []]
},
{
 "id": 15,
 "name": "edited-path-binary-at-head-absent-at-base",
 "base_commit": "root",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"code.py": {"seq": [["s", 0, 10]]}}
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"code.py": {"hex": "62696e006172790a"}},
   "listing": ["source $source", "edited code.py"]
  }
 ],
 "expected": [0, 0, []]
},
{
 "id": 16,
 "name": "edited-path-text-at-base-becomes-binary",
 "base_commit": "base",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "base",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/f.txt": {"hex": "62696e006172790a"}},
   "listing": ["source $source", "edited vendor/f.txt"]
  }
 ],
 "expected": [0, 0, []]
},
{
 "id": 17,
 "name": "unlisted-hand-written-file-at-base-becomes-edited",
 "base_commit": "root",
 "steps": [
  {
   "commit": "root",
   "branch": "main",
   "files": {"README.md": "base\n", "vendor/f.txt": {"seq": [["b", 0, 50]]}}
  },
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 50]]}}
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 45], ["e", 0, 5]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  }
 ],
 "expected": [100, 0, []]
},
{
 "id": 18,
 "name": "edited-file-untouched-by-pr",
 "base_commit": "base",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "base",
   "branch": "main",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  },
  {
   "commit": "pr",
   "branch": "main",
   "files": {"notes.txt": {"seq": [["n", 0, 3]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  }
 ],
 "expected": [3, 0, []]
},
{
 "id": 19,
 "name": "base-ref-advanced-past-merge-base-file-absent-at-merge-base",
 "base_commit": "main-advance",
 "base_ref": "main",
 "run_branch": "pr",
 "steps": [
  {"commit": "root", "branch": "main", "files": {"README.md": "base\n"}},
  {
   "commit": "source",
   "branch": "src",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["s", 0, 100]]}}
  },
  {
   "commit": "main-advance",
   "branch": "main",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["d", 0, 30], ["s", 30, 70]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  },
  {
   "commit": "pr",
   "branch": "pr",
   "start_from": "root",
   "files": {"vendor/f.txt": {"seq": [["e", 0, 12], ["s", 12, 88]]}},
   "listing": ["source $source", "edited vendor/f.txt"]
  }
 ],
 "expected": [24, 0, []]
}
]

"""
)


def file_bytes(spec: str | dict[str, list[list[object]]]) -> bytes:
    if isinstance(spec, str):
        return spec.encode()
    if "hex" in spec:
        return bytes.fromhex(str(spec["hex"]))
    return "".join(
        f"{prefix} {i}\n"
        for prefix, start, count in spec["seq"]
        for i in range(int(str(start)), int(str(start)) + int(str(count)))
    ).encode()


def build_scenario(tmp_path: Path, scenario: dict[str, Any]) -> tuple[Path, str]:
    """Replay the recipe's steps in a temporary repo; return it with the --base argument."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    shas: dict[str, str] = {}
    for step in scenario["steps"]:
        branch = step["branch"]
        if branch in git(repo, "branch", "--format=%(refname:short)").split():
            git(repo, "checkout", "-q", branch)
            start = step.get("start_from")
            assert start is None or git(repo, "rev-parse", "HEAD") == shas[start]
        elif step.get("start_from"):
            git(repo, "checkout", "-q", "-b", branch, shas[step["start_from"]])
        for name in step.get("remove", []):
            git(repo, "rm", "-q", name)
        files = {name: file_bytes(spec) for name, spec in step.get("files", {}).items()}
        if "listing" in step:
            text = "".join(f"{row}\n" for row in step["listing"])
            files[pr_size.LISTING] = text.replace("$source", shas.get("source", "")).encode()
        shas[step["commit"]] = commit(repo, step["commit"], files)
    git(repo, "checkout", "-q", scenario.get("run_branch", "main"))
    return repo, scenario.get("base_ref") or shas[scenario["base_commit"]]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: f"{s['id']}-{s['name']}")
def test_answer_key_scenario(tmp_path: Path, scenario: dict[str, Any]) -> None:
    counted, code, mismatches = scenario["expected"]
    repo, base = build_scenario(tmp_path, scenario)
    done = result(repo, base)
    assert f"counted lines: {counted} (limit 800)" in done.stdout
    assert [r for r in done.stdout.splitlines() if r.startswith("copy mismatch: ")] == [
        f"copy mismatch: {m}" for m in mismatches
    ]
    assert done.returncode == code, done.stdout + done.stderr
    assert pr_size.pr_lines(base, repo) == counted
