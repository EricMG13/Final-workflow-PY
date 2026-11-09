"""S02-C05: render_owner_slice captures (verifies and builds) the run three times, not six.

`_capture` is stubbed, so this checks the call pattern and the stale refusal only; the byte-level
rendering is covered by test_owner_rendering.py (slow, not run here)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from deploy_workflow import owner_rendering as r

TREE = {"report.html": b"<html/>", r.RECEIPT_NAME: b"{}"}


def _stub(monkeypatch: pytest.MonkeyPatch, captures: list[object]) -> list[int]:
    calls: list[int] = []

    def capture(*args: object) -> object:
        calls.append(1)
        return captures[min(len(calls), len(captures)) - 1]

    monkeypatch.setattr(r, "_capture", capture)
    monkeypatch.setattr(r, "OwnerRenderReceipt", SimpleNamespace(from_wire=lambda raw: "W"))
    return calls


def test_one_render_captures_three_times(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Hand-derived: the first capture, one stale check on the stage, one on the renamed target.
    calls = _stub(monkeypatch, [SimpleNamespace(tree=TREE, wire="W")])
    (tmp_path / "store").mkdir()
    out = r.render_owner_slice(tmp_path / "store", tmp_path / "receipt.json", None, tmp_path / "o")
    assert len(calls) == 3
    assert out == tmp_path / "o" / "report.html"
    assert (tmp_path / "o" / "report.html").read_bytes() == b"<html/>"


@pytest.mark.parametrize("changed_at", [2, 3])
def test_a_store_that_changes_after_the_first_capture_is_refused_as_stale(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, changed_at: int
) -> None:
    same = SimpleNamespace(tree=TREE, wire="W")
    other = SimpleNamespace(tree={**TREE, "report.html": b"<html>2</html>"}, wire="W")
    captures = [same] * (changed_at - 1) + [other]
    _stub(monkeypatch, captures)
    (tmp_path / "store").mkdir()
    with pytest.raises(ValueError, match="owner_render_(stale|delivery)"):
        r.render_owner_slice(tmp_path / "store", tmp_path / "receipt.json", None, tmp_path / "o")
    if changed_at == 2:  # before the rename: the stage is removed and nothing is published
        assert not (tmp_path / "o").exists()
        assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".owner-render")] == []
