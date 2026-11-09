"""PR size and copy check: each test builds its own temporary git repo."""

import os
import subprocess
import sys
from pathlib import Path

from tools import pr_size

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "pr_size.py"
IDENT = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
UNKNOWN_SHA = "0123456789abcdef0123456789abcdef01234567"
# The developer's own git config (hooks, signing, aliases) must not reach the temporary repos.
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *IDENT, *args], cwd=repo, check=True, capture_output=True, text=True, env=GIT_ENV
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
        env=GIT_ENV,
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
