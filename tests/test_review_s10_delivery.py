"""S10 review: deliveries publish exclusively (no rename over a directory another writer made),
the owner renderer's Windows tree reader refuses with an `owner_render_*` code, a `str`
destination works, and one owner render replays the run three times, not six. Component probes
over genuine stores (source slice, financial gap case) or a real prepared pack with the closed-run
verifier patched (owner, as in `test_owner_rendering`'s run-context section)."""

from __future__ import annotations

import importlib
import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii.contracts import Run
from deploy_vii.execution import Execution
from deploy_workflow import owner_rendering as g2
from deploy_workflow import rendering

connected: Any = importlib.import_module("test_connected_render")
fw: Any = importlib.import_module("test_financial_workflow")


def test_publish_directory_never_replaces_an_existing_empty_directory(tmp_path: Path) -> None:
    stage = tmp_path / ".stage"
    stage.mkdir()
    (stage / "report.html").write_text("rendered")
    destination = tmp_path / "delivery"
    destination.mkdir()  # another writer reserved it
    with pytest.raises(FileExistsError):
        rendering.publish_directory(stage, destination)
    assert list(destination.iterdir()) == []
    assert (stage / "report.html").read_text() == "rendered"


def test_publish_directory_moves_the_complete_stage(tmp_path: Path) -> None:
    stage = tmp_path / ".stage"
    (stage / "nested").mkdir(parents=True)
    (stage / "report.html").write_text("rendered")
    (stage / "nested" / "a.json").write_text("{}")
    rendering.publish_directory(stage, tmp_path / "delivery")
    assert not stage.exists()
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")) == [
        "delivery",
        "delivery/nested",
        "delivery/nested/a.json",
        "delivery/report.html",
    ]


def test_publish_directory_refuses_a_reservation_filled_meanwhile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage = tmp_path / ".stage"
    stage.mkdir()
    (stage / "report.html").write_text("ours")
    destination = tmp_path / "delivery"
    real_rename = os.rename

    def other_writer_first(src: Any, dst: Any) -> None:
        (Path(dst) / "theirs.html").write_text("theirs")
        real_rename(src, dst)

    monkeypatch.setattr(os, "rename", other_writer_first)
    with pytest.raises(FileExistsError):
        rendering.publish_directory(stage, destination)
    assert [p.name for p in destination.iterdir()] == ["theirs.html"]
    assert (stage / "report.html").read_text() == "ours"


def _hide(monkeypatch: pytest.MonkeyPatch, destination: Path) -> None:
    """The renderer's last existence check runs before another writer creates `destination`."""
    real_exists = Path.exists

    def exists(self: Path, *args: Any, **kwargs: Any) -> bool:
        return False if self == destination else real_exists(self, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", exists)


def test_source_slice_render_refuses_a_destination_made_after_its_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory, receipt_path, _ = connected._case(tmp_path, gap=True)
    destination = tmp_path / "published"
    destination.mkdir()
    _hide(monkeypatch, destination)
    with pytest.raises(ValueError, match="^source_slice_render_refused$"):
        rendering.render_source_slice(directory, receipt_path, destination)
    monkeypatch.undo()
    assert list(destination.iterdir()) == []
    assert not list(tmp_path.glob(".source-slice-*"))


def test_financial_render_refuses_a_destination_made_after_its_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from deploy_workflow.financial_rendering import render_financial_slice

    store, receipt, _ = fw.completed_financial_case(tmp_path / "gap", gap=True)
    destination = tmp_path / "published"
    destination.mkdir()
    _hide(monkeypatch, destination)
    with pytest.raises(ValueError, match="^financial_slice_render_refused$"):
        render_financial_slice(store, receipt, None, destination)
    monkeypatch.undo()
    assert list(destination.iterdir()) == []
    assert not list(tmp_path.glob(".financial-slice-*"))


# ------------------------------------------------------------------------------------- owner

_RUN = Run(
    run_id="s10-sim",
    issuer_id="northbridge-synthetic",
    issuer_name="Northbridge Synthetic Group",
    as_of=date(2026, 1, 10),
    case_kind="synthetic",
    pathway="credit_snapshot",
    requested_modules=("CP-1", "CP-MODEL", "CP-1A", "CP-2"),
)


def _sim(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A real prepared pack in a real store, with the closed-run verifier patched (no module
    has a head, so every module is idle)."""
    from deploy_vii.preparation import PreparationRequest, SourceRequest, prepare

    src = root / "src"
    src.mkdir(parents=True)
    (src / "b.txt").write_text("borrower text\n")
    sources = (SourceRequest(source_id="business", path="b.txt", media_type="text/plain"),)
    pack = prepare(PreparationRequest(run=_RUN, sources=sources), src, root / "prepared")
    Execution.create(root / "store", pack)
    (root / "owner-run.json").write_bytes(b"{}")
    store = Execution(root / "store")
    snap = store.read()
    receipt = SimpleNamespace(
        run=pack.run,
        refusals=(),
        model=None,
        snapshot_sha256=snap.content_hash(),
        pack_sha256=store.pack(snap).content_hash(),
        heads=[],
        plan=(),
        content_hash=lambda: "0" * 64,
    )
    monkeypatch.setattr(g2, "_parse_receipt", lambda raw: receipt)
    monkeypatch.setattr(g2, "verify_owner_run_receipt", lambda *a, **k: None)
    monkeypatch.setattr(g2, "_outcome_rules", lambda r, s, h: "complete")
    monkeypatch.setattr(g2, "_sections", lambda *a: ())
    return root / "store", root / "owner-run.json"


def test_owner_render_accepts_a_str_destination_and_replays_the_run_three_times(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, receipt = _sim(tmp_path, monkeypatch)
    real_capture = g2._capture
    captures: list[int] = []

    def counted(*args: Any) -> Any:
        captures.append(1)
        return real_capture(*args)

    monkeypatch.setattr(g2, "_capture", counted)
    destination = str(tmp_path / "delivery")
    html = g2.render_owner_slice(store, receipt, None, destination)
    assert html == Path(destination) / "report.html" and html.is_file()
    assert len(captures) == 3
    g2.verify_owner_rendered_slice(store, receipt, None, Path(destination))


def test_owner_render_refuses_a_destination_made_after_its_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, receipt = _sim(tmp_path, monkeypatch)
    destination = tmp_path / "out" / "delivery"
    destination.parent.mkdir()
    real_lexists = os.path.lexists
    checks: list[int] = []

    def lexists(path: Any) -> bool:
        if Path(path) == destination:
            checks.append(1)
            if len(checks) == 2:  # the last check; another writer creates it just after
                destination.mkdir()
                return False
        return real_lexists(path)

    monkeypatch.setattr(os.path, "lexists", lexists)
    with pytest.raises(ValueError, match="^owner_render_destination_exists$"):
        g2.render_owner_slice(store, receipt, None, destination)
    assert len(checks) == 2
    assert list(destination.iterdir()) == []
    assert not list(destination.parent.glob(".owner-render-*"))


def test_windows_tree_reader_reads_a_regular_tree_as_the_posix_one_does(tmp_path: Path) -> None:
    (tmp_path / "d" / "sub").mkdir(parents=True)
    (tmp_path / "d" / "report.html").write_bytes(b"<html>")
    (tmp_path / "d" / "sub" / "x.json").write_bytes(b"{}")
    out: dict[str, bytes] = {}
    g2._read_tree_windows(tmp_path / "d", out)
    assert out == {"report.html": b"<html>", "sub/x.json": b"{}"} == g2._read_tree(tmp_path / "d")


@pytest.mark.parametrize("case", ["missing", "root-link", "entry-link", "open-fails"])
def test_windows_tree_reader_refuses_with_an_owner_render_code(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "report.html").write_bytes(b"<html>")
    directory = tmp_path / "d"
    if case == "root-link":
        directory.symlink_to(real, target_is_directory=True)
    elif case != "missing":
        directory.mkdir()
        (directory / "report.html").write_bytes(b"<html>")
    if case == "entry-link":
        (directory / "linked").symlink_to(real, target_is_directory=True)
    if case == "open-fails":

        def regular_open(path: Path, options: int, mode: int = 0o600) -> int:
            raise OSError("reparse points are not accepted")

        monkeypatch.setattr(g2, "regular_open", regular_open)
    with pytest.raises(ValueError, match="^owner_render_delivery$"):
        g2._read_tree_windows(directory, {})
