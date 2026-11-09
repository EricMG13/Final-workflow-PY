"""The live-run event log: line format, tolerant reading and the fixed stop reasons."""

import json
import os
from pathlib import Path

import pytest

from deploy_workflow.model.adapter import LivePauseInForce
from deploy_workflow.model.budget import BudgetExhausted, OverrunStop, RunStopped
from deploy_workflow.run_events import EVENTS, append_event, read_events, stop_reason


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (BudgetExhausted("cap"), "budget"),
        (OverrunStop("overrun"), "budget"),
        (RunStopped("the run is stopped: 'call-1' has an unknown charge"), "provider"),
        (RuntimeError("cpos_live_stopped: sent_known; charge=0.5; overrun=True"), "budget"),
        (RuntimeError("cpos_live_stopped: sent_unknown; charge=None; overrun=False"), "provider"),
        (ValueError("cpos_module_failed: CP-1: bad"), "checker"),
        (RuntimeError("cpos_live_not_accepted: CP-1 not accepted within bounds"), "checker"),
        (ValueError("cpos_retained_rejected: CP-1: bad"), "checker"),
        (RuntimeError("cpos_interrupted: stop"), "interrupted"),
        (ValueError("cpos_live_already_started: resume"), "interrupted"),
        (LivePauseInForce("no ruling"), "ruling"),
        (ValueError("x"), "other"),
    ],
)
def test_stop_reason(error: BaseException, reason: str) -> None:
    assert stop_reason(error) == reason


def test_append_writes_one_ascii_line_per_event(tmp_path: Path) -> None:
    append_event(tmp_path / "run", "turn", module="CP-1", turn=1, spent_usd="0.5")
    append_event(tmp_path / "run", "stopped", reason="café")
    raw = (tmp_path / "run" / EVENTS).read_bytes()
    raw.decode("ascii")
    first, second = (json.loads(line) for line in raw.splitlines())
    assert (first["event"], first["module"], first["turn"], first["spent_usd"]) == (
        "turn",
        "CP-1",
        1,
        "0.5",
    )
    assert len(first["at"]) == 20 and first["at"].endswith("Z")
    assert second["reason"] == "café"


def test_read_events_drops_a_last_line_cut_mid_json(tmp_path: Path) -> None:
    path = tmp_path / EVENTS
    path.write_bytes(b'{"at": "t", "event": "a"}\n{"at": "t", "event": "b"}\n{"at": "t", "ev')
    assert [e["event"] for e in read_events(path)] == ["a", "b"]


def test_read_events_rejects_a_bad_earlier_line(tmp_path: Path) -> None:
    path = tmp_path / EVENTS
    path.write_bytes(b'{"event": "a"}\nnot json\n{"event": "b"}\n')
    with pytest.raises(ValueError, match="line 2"):
        read_events(path)


def test_read_events_reads_at_most_the_limit(tmp_path: Path) -> None:
    path = tmp_path / EVENTS
    path.write_bytes(b'{"event": "a"}\n{"event": "b"}\n')
    assert [e["event"] for e in read_events(path, limit=15)] == ["a"]


@pytest.mark.skipif(os.name == "nt", reason="resource and SIGXFSZ do not exist on Windows")
def test_an_append_that_fails_part_way_leaves_the_log_as_it_was(tmp_path: Path) -> None:
    import resource
    import signal

    append_event(tmp_path, "module_started", module="CP-0")
    size = (tmp_path / EVENTS).stat().st_size
    previous = signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
    resource.setrlimit(resource.RLIMIT_FSIZE, (size + 20, hard))  # room for 20 more bytes only
    try:
        with pytest.warns(RuntimeWarning, match="run event not recorded: turn"):
            append_event(tmp_path, "turn", module="CP-0", turn=1, spent_usd="0")
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE, (soft, hard))
        signal.signal(signal.SIGXFSZ, previous)
    append_event(tmp_path, "module_accepted", module="CP-0")
    assert [e["event"] for e in read_events(tmp_path / EVENTS)] == [
        "module_started",
        "module_accepted",
    ]
