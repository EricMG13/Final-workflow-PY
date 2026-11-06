"""S18 review fixes: ``brief.json`` is written as LF bytes on every platform and created once;
intake's supplied path checks the fence with ``retrieved`` as its docstring says; ``dest_dir`` is
made once, and only when something is accepted."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.research import brief as b
from deploy_workflow.research import intake as it
from deploy_workflow.research.contracts import Anchor, BriefInvalid, ResearchBrief

ANCHOR = Anchor(cp0_sha256="c" * 64, cp1_sha256="d" * 64)


def locked(tmp_path: Path) -> tuple[Path, ResearchBrief]:
    path = tmp_path / "research" / "brief.json"
    brief = b.lock_brief(
        issuer_id="acme",
        run_id="run-1",
        as_of=date(2026, 1, 10),
        cutoff=date(2026, 1, 10),
        context_questions=[("How is demand moving?", "CP-2")],
        tailored=[],
        anchor=ANCHOR,
        path=path,
    )
    return path, brief


def test_brief_json_is_lf_bytes_even_where_text_mode_writes_crlf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Text mode translates "\n" to os.linesep on write, which is "\r\n" on Windows: a text-mode
    # write here is made to translate as it would there.
    real_open = Path.open

    def windows_open(self: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        writes = any(flag in mode for flag in "wxa")
        if writes and "b" not in mode and kwargs.get("newline") is None:
            kwargs["newline"] = "\r\n"
        return real_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", windows_open)
    path, brief = locked(tmp_path)
    data = path.read_bytes()
    assert b"\r" not in data and data.endswith(b"}\n")
    body = json.loads(data)
    assert body["run_id"] == "run-1" and body["brief_sha256"] == brief.brief_sha256
    expected = json.dumps(body, sort_keys=True, indent=1, ensure_ascii=False) + "\n"
    assert data == expected.encode("utf-8")
    assert b.load_locked_brief(path, brief.brief_sha256) == brief


def test_a_locked_brief_is_never_overwritten(tmp_path: Path) -> None:
    path, brief = locked(tmp_path)
    before = path.read_bytes()
    with pytest.raises(BriefInvalid, match="brief already locked at"):
        b.write_locked_brief(path, brief)
    assert path.read_bytes() == before


def rows(*names: str) -> tuple[it.ManifestRow, ...]:
    return it.parse_rows(
        [
            {
                "path": name,
                "family": "fam-a",
                "published": "2025-12-01",
                "locator": f"https://x.example/{name}",
                "tag": "research",
            }
            for name in names
        ]
    )


def run(tmp_path: Path, names: tuple[str, ...], **kwargs: Any) -> it.IntakeResult:
    return it.intake(
        rows(*names),
        base_dir=tmp_path,
        as_of=date(2026, 1, 10),
        cutoff=date(2026, 1, 10),
        today=date(2026, 1, 10),
        **kwargs,
    )


def test_the_supplied_path_checks_the_fence_with_retrieved(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"Plain evidence text.\n")
    accepted = run(tmp_path, ("a.txt",), dest_dir=None, retrieved="2026-01-10T09:00:00Z")
    assert [i.item_id for i in accepted.accepted] == ["ev-1"] and accepted.refused == ()
    # A retrieval time the fence header cannot hold refuses the item, as it does for a url row.
    refused = run(tmp_path, ("a.txt",), dest_dir=None, retrieved="bad>>>time")
    assert refused.accepted == ()
    assert [r.locator for r in refused.refused] == ["https://x.example/a.txt"]


def test_dest_dir_is_made_only_when_an_item_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"Plain evidence text.\n")
    (tmp_path / "b.txt").write_bytes(b"Second item.\n")
    none_dir = tmp_path / "none"
    result = run(tmp_path, ("missing.txt",), dest_dir=none_dir)
    assert result.accepted == () and not none_dir.exists()
    dest = tmp_path / "out"
    result = run(tmp_path, ("a.txt", "b.txt"), dest_dir=dest)
    assert sorted(p.name for p in dest.iterdir()) == ["ev-1.txt", "ev-2.txt"]
    assert (dest / "ev-2.txt").read_bytes() == b"Second item.\n"


def test_a_directory_is_refused_as_not_a_regular_file(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    result = run(tmp_path, ("sub",), dest_dir=None)
    assert [r.reason for r in result.refused] == [
        "evidence item https://x.example/sub cannot be opened (not a regular file)"
    ]
