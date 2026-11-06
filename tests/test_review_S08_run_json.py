"""S08 review regression: a run killed while writing run.json under the old fixed temp name
(run.json.tmp left behind) can still be closed by a resume. Synthetic gap pack; offline."""

from pathlib import Path
from typing import NoReturn

import pytest
from test_run_pathway import (  # noqa: F401  (pytest fixtures)
    Kill,
    args,
    gap_world,
    no_network,
    pack_helpers,
    rp,
    scripted_complete,
)

from deploy_workflow.platform_io import atomic_write


def test_a_leftover_run_json_tmp_does_not_block_the_resume(args, monkeypatch):  # noqa: F811
    checked, run_dir, factory = gap_world(args, monkeypatch)
    with monkeypatch.context() as m:
        scripted_complete(m, [pack_helpers.ok(pack_helpers.read_identity()),
                              pack_helpers.ok(pack_helpers.gap_submit())])

        def die(*a: object, **k: object) -> NoReturn:
            raise Kill("after the seal")

        m.setattr(rp, "verify_owner_run_receipt", die)
        with pytest.raises(Kill):
            rp._run_pathway(checked, run_dir, args["adapter"], factory)
    (run_dir / "run.json.tmp").write_bytes(b'{"partial')
    scripted_complete(monkeypatch, [])
    outcome = rp._run_pathway(checked, run_dir, args["adapter"], factory, resume=True)
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason.startswith("SealedWithoutRunRecord")
    assert (run_dir / "run.json").is_file()
    assert not (run_dir / "run.json.tmp").exists()
    assert not list(run_dir.glob(".run.json.*.tmp"))


def test_atomic_write_replaces_and_leaves_no_temp(tmp_path: Path):
    target = tmp_path / "state.json"
    atomic_write(target, b"one")
    atomic_write(target, b"two")
    assert target.read_bytes() == b"two"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json"]


def test_atomic_write_failure_keeps_the_old_file_and_removes_its_temp(tmp_path, monkeypatch):
    target = tmp_path / "state.json"
    target.write_bytes(b"old")

    def refuse(source: object, destination: object) -> NoReturn:
        raise PermissionError("held open")

    monkeypatch.setattr("deploy_workflow.platform_io.os.replace", refuse)
    monkeypatch.setattr("deploy_workflow.platform_io.time.sleep", lambda seconds: None)
    with pytest.raises(PermissionError):
        atomic_write(target, b"new")
    assert target.read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json"]
