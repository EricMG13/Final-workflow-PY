"""Replay reads the earlier run once: the plan carries the authenticated `_Earlier`."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_workflow import replay


class _Stop(Exception):
    pass


def _retained(directory: Path) -> Any:
    # Hand-derived: replay_module must use this object (its pack check raises _Stop) and must not
    # construct a new _Earlier from the path (which would raise ReplayRefused: nothing there).
    def pack(snapshot: object) -> None:
        raise _Stop

    return SimpleNamespace(directory=directory, store=SimpleNamespace(pack=pack), snapshot=None)


def test_replay_module_uses_the_plans_retained_read(tmp_path: Path) -> None:
    earlier = tmp_path / "gone"
    with pytest.raises(_Stop):
        replay.replay_module(
            None,  # type: ignore[arg-type]
            earlier,
            "CP-0",
            execution=tmp_path,
            retained=_retained(earlier),
        )


def test_a_read_of_another_directory_is_refused_before_the_pack_check(tmp_path: Path) -> None:
    # A plan's read stands for its own earlier run only; no other directory replays from it.
    with pytest.raises(replay.ReplayRefused, match="the plan's read is of"):
        replay.replay_module(
            None,  # type: ignore[arg-type]
            tmp_path / "other",
            "CP-0",
            execution=tmp_path,
            retained=_retained(tmp_path / "gone"),
        )


def test_replay_module_without_retained_reads_the_directory(tmp_path: Path) -> None:
    with pytest.raises(replay.ReplayRefused):
        replay.replay_module(None, tmp_path / "gone", "CP-0", execution=tmp_path)  # type: ignore[arg-type]


def test_plan_retained_is_not_part_of_equality() -> None:
    a = replay.ReplayPlan(Path("x"), "r", ("CP-0",), ())
    b = replay.ReplayPlan(Path("x"), "r", ("CP-0",), (), (), retained=_retained(Path("x")))
    assert a == b and hash(a) == hash(b) and "retained" not in repr(b)
