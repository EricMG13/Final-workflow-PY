"""PR size and copy check.

Files copied byte-identical from a pinned commit of another repository are listed in
tools/copied-from.txt and do not count toward the PR line cap.

Listing format: first line ``source <40-hex sha>``, then one repo-relative path per line
(copied byte-identical, or deleted upstream), or ``edited <path>`` for a file copied from the
sha and then edited by hand: it counts only its difference from the sha. A listing with no
non-blank lines means "no copies".
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

LIMIT = 800
LISTING = "tools/copied-from.txt"
SKIP_PREFIXES = ("tests/fixtures/", "cases/", "apps/issuer-library/web/testdata/")
ANSWER_KEY_DIR = "apps/issuer-library/designs/"
ANSWER_KEY_SUFFIX = "-answer-key.json"
LOCKFILE = "uv.lock"
SOURCE_LINE = re.compile(r"source ([0-9a-fA-F]{40})")
EDITED_PREFIX = "edited "


def _git(repo: Path, *args: str) -> bytes:
    done = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    return done.stdout


def _parse_listing(listing: Path) -> tuple[str, list[str], list[str]] | None:
    """Return (sha, copied paths, edited paths), or None when the listing is absent or empty."""
    if not listing.exists():
        return None
    rows = [r.strip() for r in listing.read_text(encoding="utf-8").splitlines() if r.strip()]
    if not rows:
        return None
    match = SOURCE_LINE.fullmatch(rows[0])
    if match is None:
        raise ValueError(f"{listing}: first line must be 'source <40-hex sha>', got {rows[0]!r}")
    edited = [
        r.removeprefix(EDITED_PREFIX).strip() for r in rows[1:] if r.startswith(EDITED_PREFIX)
    ]
    copied = [r for r in rows[1:] if not r.startswith(EDITED_PREFIX)]
    return match.group(1), copied, edited


def _exists_at(repo: Path, sha: str, path: str) -> bool:
    done = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}:{path}"], cwd=repo, check=False, capture_output=True
    )
    return done.returncode == 0


def copied_mismatches(listing: Path, repo: Path) -> list[str]:
    """Listed paths whose bytes differ from the source commit (or are missing/extra)."""
    parsed = _parse_listing(listing)
    if parsed is None:
        return []
    sha, paths, edited = parsed
    known = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=repo, check=False, capture_output=True
    )
    if known.returncode != 0:
        raise ValueError(f"source commit {sha} is not in this repository; fetch it first")
    bad: list[str] = []
    for path in paths:
        target = repo / path
        if _exists_at(repo, sha, path):
            expected = _git(repo, "show", f"{sha}:{path}")
            if not target.is_file() or target.read_bytes() != expected:
                bad.append(path)
        elif target.exists():
            bad.append(path)
    for path in edited:
        if not _exists_at(repo, sha, path) or not (repo / path).is_file():
            bad.append(path)
    return sorted(set(bad))


def _is_excluded(path: str) -> bool:
    if path.startswith(SKIP_PREFIXES) or path == LISTING:
        return True
    if path.rsplit("/", 1)[-1] == LOCKFILE:
        return True
    rest = path.removeprefix(ANSWER_KEY_DIR)
    return rest != path and "/" not in rest and rest.endswith(ANSWER_KEY_SUFFIX)


def _edit_lines(repo: Path, sha: str, path: str) -> int:
    """Added plus deleted lines of one file, HEAD against the source commit."""
    out = _git(repo, "diff", "--numstat", "--no-renames", sha, "HEAD", "--", path)
    if not out.strip():
        return 0
    added, deleted, _ = out.decode("utf-8").split("\t", 2)
    return 0 if added == "-" or deleted == "-" else int(added) + int(deleted)


def pr_lines(base: str, repo: Path) -> int:
    """Added plus deleted lines in base...HEAD, minus copies, fixtures and lockfiles."""
    parsed = _parse_listing(repo / LISTING)
    sha, copied, edited = (
        (parsed[0], set(parsed[1]), set(parsed[2])) if parsed else ("", set(), set())
    )
    out = _git(repo, "diff", "--numstat", "--no-renames", "-z", f"{base}...HEAD")
    total = 0
    for record in out.decode("utf-8").split("\0"):
        if not record:
            continue
        added, deleted, path = record.split("\t", 2)
        if path in copied or _is_excluded(path) or added == "-" or deleted == "-":
            continue
        if path in edited:
            total += _edit_lines(repo, sha, path)
        else:
            total += int(added) + int(deleted)
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR size and copy check")
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args(argv)
    try:
        top = _git(Path.cwd(), "rev-parse", "--show-toplevel").decode("utf-8").strip()
        repo = Path(top)
        mismatches = copied_mismatches(repo / LISTING, repo)
        total = pr_lines(args.base, repo)
    except ValueError as err:
        print(err, file=sys.stderr)
        return 1
    print(f"counted lines: {total} (limit {LIMIT})")
    for path in mismatches:
        print(f"copy mismatch: {path}")
    return 1 if mismatches or total > LIMIT else 0


if __name__ == "__main__":
    raise SystemExit(main())
