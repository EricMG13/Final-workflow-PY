"""PR size and copy check.

Files copied byte-identical from a pinned commit of another repository are listed in
tools/copied-from.txt and do not count toward the PR line cap. The check measures HEAD (the
listing and the files are read from commits), not the working tree.

Listing format: first line ``source <40-hex sha>``, then one repo-relative path per line
(copied byte-identical, or deleted upstream), or ``edited <path>`` for a file copied from the
sha and then edited by hand: it counts only its difference from the sha. A listing with no
non-blank lines means "no copies".
"""

import argparse
import re
import shlex
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


def _parse_listing(text: str, name: str) -> tuple[str, list[str], list[str]] | None:
    """Return (sha, copied paths, edited paths), or None when the listing is empty."""
    rows = [r.strip() for r in text.splitlines() if r.strip()]
    if not rows:
        return None
    match = SOURCE_LINE.fullmatch(rows[0])
    if match is None:
        raise ValueError(f"{name}: first line must be 'source <40-hex sha>', got {rows[0]!r}")
    edited = [
        r.removeprefix(EDITED_PREFIX).strip() for r in rows[1:] if r.startswith(EDITED_PREFIX)
    ]
    copied = [r for r in rows[1:] if not r.startswith(EDITED_PREFIX)]
    return match.group(1), copied, edited


def _entries(repo: Path, rev: str, paths: list[str]) -> dict[str, tuple[str, str, str]]:
    """(mode, type, object id) of each path that exists at rev; one git call."""
    if not paths:
        return {}
    out = _git(repo, "ls-tree", "-z", rev, "--", *paths).decode("utf-8")
    found: dict[str, tuple[str, str, str]] = {}
    for record in out.split("\0"):
        if record:
            meta, name = record.split("\t", 1)
            mode, kind, oid = meta.split(" ")
            found[name] = (mode, kind, oid)
    return found


def _read_listing(repo: Path, listing: Path) -> tuple[str, list[str], list[str]] | None:
    """The listing as committed at HEAD; None when HEAD has no such file or it is empty."""
    try:
        name = listing.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        raise ValueError(f"{listing}: the listing must be a path inside {repo}") from None
    if name not in _entries(repo, "HEAD", [name]):
        return None
    return _parse_listing(_git(repo, "show", f"HEAD:{name}").decode("utf-8"), name)


def copied_mismatches(listing: Path, repo: Path) -> list[str]:
    """Listed paths whose committed entry at HEAD differs from the source commit's.

    Both the listing and every path are read from HEAD, not the working tree, so this checks
    the same committed state as ``pr_lines``. ``listing`` must name a path inside ``repo``.
    A plain path matches when mode, type and object id are equal; a path absent at the source
    must be absent at HEAD; an edited path must be a blob at both; a tree is a mismatch.
    """
    parsed = _read_listing(repo, listing)
    if parsed is None:
        return []
    sha, paths, edited = parsed
    known = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=repo, check=False, capture_output=True
    )
    if known.returncode != 0:
        raise ValueError(f"source commit {sha} is not in this repository; fetch it first")
    names = sorted({*paths, *edited})
    there = _entries(repo, sha, names)
    here = _entries(repo, "HEAD", names)
    bad: list[str] = []
    for path in paths:
        if path in there:
            if there[path][1] != "blob" or here.get(path) != there[path]:
                bad.append(path)
        elif path in here:
            bad.append(path)
    for path in edited:
        if there.get(path, ("", "", ""))[1] != "blob" or here.get(path, ("", "", ""))[1] != "blob":
            bad.append(path)
    return sorted(set(bad))


def _is_excluded(path: str) -> bool:
    if path.startswith(SKIP_PREFIXES) or path == LISTING:
        return True
    if path.rsplit("/", 1)[-1] == LOCKFILE:
        return True
    rest = path.removeprefix(ANSWER_KEY_DIR)
    return rest != path and "/" not in rest and rest.endswith(ANSWER_KEY_SUFFIX)


def _edit_lines(repo: Path, sha: str, path: str) -> int | None:
    """Added plus deleted lines of one file, HEAD against the source commit.

    None when git reports the file binary (either side), so the caller keeps its range count.
    """
    out = _git(repo, "diff", "--numstat", "--no-renames", sha, "HEAD", "--", path)
    if not out.strip():
        return 0
    added, deleted, _ = out.decode("utf-8").split("\t", 2)
    return None if added == "-" or deleted == "-" else int(added) + int(deleted)


def pr_lines(base: str, repo: Path) -> int:
    """Added plus deleted lines in base...HEAD, minus copies, fixtures and lockfiles."""
    parsed = _read_listing(repo, repo / LISTING)
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
        own = _edit_lines(repo, sha, path) if path in edited else None
        total += int(added) + int(deleted) if own is None else own
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
    except subprocess.CalledProcessError as err:
        detail = err.stderr.decode("utf-8", "replace").strip() if err.stderr else ""
        print(f"git failed: {shlex.join(map(str, err.cmd))}: {detail}", file=sys.stderr)
        return 1
    print(f"counted lines: {total} (limit {LIMIT})")
    for path in mismatches:
        print(f"copy mismatch: {path}")
    return 1 if mismatches or total > LIMIT else 0


if __name__ == "__main__":
    raise SystemExit(main())
