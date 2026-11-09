"""PR size and copy check: each test builds its own temporary git repo."""

import subprocess
import sys
from pathlib import Path

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
    """Base holds a different 1000-line file; source holds 900; HEAD edits the source copy."""
    repo, base = make_repo(tmp_path, {"vendor/big.txt": lines(1000)[::-1]})
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
