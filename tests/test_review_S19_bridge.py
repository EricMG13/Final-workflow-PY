"""S19 review regressions: the CP-OS bridge's status after a failure, and its release notes.

The provider is the offline fake from test_cpos_launch; no paid call is made.
"""

from __future__ import annotations

import json
import warnings
from decimal import Decimal

import pytest
import test_cpos_launch
from test_cpos_app import bridge, started, status_of

provider = test_cpos_launch.provider  # The same fake provider fixture.


def fails_after_a_paid_call(*args, **kwargs):
    kwargs["on_start"](type("Task", (), {"module_id": "CP-1"})())
    raise OSError(28, "No space left on device")


def test_any_failure_after_paid_calls_keeps_the_spend_in_status(
    tmp_path, provider, monkeypatch, capsys
):
    folder, _ = started(tmp_path, provider)
    monkeypatch.setattr(bridge, "run_live_handoffs", fails_after_a_paid_call)
    monkeypatch.setattr(bridge.sys, "argv", ["bridge.py", "start", str(folder)])
    with pytest.raises(SystemExit):
        bridge.main()
    status = status_of(folder)
    assert status["state"] == "failed"
    assert Decimal(status["spent_usd"]) >= 0
    assert status["message"] == (
        "[Errno 28] No space left on device Retained work is in the run folder; "
        "no automatic paid retry was made."
    )
    printed = json.loads(capsys.readouterr().out)
    assert printed == {"ok": False, "problems": ["[Errno 28] No space left on device"]}


def test_a_refusal_still_stops_the_run_with_its_spend(tmp_path, provider, monkeypatch):
    folder, _ = started(tmp_path, provider)

    def refuses(*args, **kwargs):
        raise ValueError("CP-2 handoff rejected")

    monkeypatch.setattr(bridge, "run_live_handoffs", refuses)
    bridge.start(folder)
    status = status_of(folder)
    assert status["state"] == "stopped" and "spent_usd" in status
    assert status["message"].startswith("CP-2 handoff rejected Retained work")


def test_only_release_failures_reach_the_complete_message_once_and_redacted(
    tmp_path, provider, monkeypatch
):
    folder, _ = started(tmp_path, provider)
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "ghu_secretvalue123")

    def finishes(*args, **kwargs):
        for _ in range(2):
            warnings.warn("adapter release failed: token ghu_secretvalue123", RuntimeWarning)
        warnings.warn("coroutine 'close' was never awaited", RuntimeWarning)

    monkeypatch.setattr(bridge, "run_live_handoffs", finishes)
    bridge.start(folder)
    status = status_of(folder)
    assert status["state"] == "complete"
    assert "ghu_secretvalue123" not in status["message"]
    assert status["message"].count("adapter release failed") == 1
    assert "never awaited" not in status["message"]


def test_the_bridge_writes_through_the_library_s_one_atomic_writer(tmp_path):
    from issuer_library import settings

    assert bridge.write_file is settings.write_atomic
    bridge.write_json(tmp_path / "status.json", {"state": "complete", "value": "é"})
    assert (tmp_path / "status.json").read_bytes() == (
        b'{\n  "state": "complete",\n  "value": "\\u00e9"\n}'
    )
    with pytest.raises(ValueError):
        bridge.write_json(tmp_path / "status.json", {"spent": float("nan")})
