"""S16 review: the budget on a platform that cannot open a directory, and the tool loop's
handling of a failed connect and of an adapter that cannot resend. Scripted adapter, no network."""

import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from _pack import failed, make_rig

from deploy_workflow.model.budget import Budget
from deploy_workflow.model.loop import StepStopped

EXEC_RESERVATIONS = ("owner-run-audit", "reservations")


def test_the_budget_works_where_a_directory_cannot_be_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_open = os.open

    def refuse_directories(path: Any, flags: int, mode: int = 0o777) -> int:
        if Path(path).is_dir():
            raise PermissionError(13, "Access is denied")  # as Windows answers
        return real_open(path, flags, mode)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "open", refuse_directories)
    budget = Budget(Decimal(10), tmp_path)
    budget.reserve("call-1", Decimal("1.5"), config_id="sol-medium")
    budget.settle("call-1", Decimal("0.25"))
    assert budget.stop_reason is None and budget.spent == Decimal("0.25")
    assert budget.reserved == Decimal(0)
    monkeypatch.undo()
    again = Budget(Decimal(10), tmp_path)
    assert again.unsettled == () and again.spent == Decimal("0.25")


def _stop(rig: Any) -> StepStopped:
    with pytest.raises(StepStopped) as caught:
        rig.loop.run()
    return caught.value


def test_a_failed_connect_is_resent_once_and_holds_nothing(tmp_path: Path) -> None:
    lost = failed("not_sent", "NotConnected", None, message="connection failed")
    rig = make_rig(tmp_path, [lost, lost])
    stopped = _stop(rig)
    assert stopped.reason == "NotConnected"
    assert rig.sleeps == [5]
    assert len(rig.records()) == 2
    assert rig.budget.reserved == Decimal(0) and rig.budget.spent == Decimal(0)
    assert rig.budget.stop_reason is None  # released holds: the run may go on later


def test_a_reconnect_that_answers_goes_on(tmp_path: Path) -> None:
    lost = failed("not_sent", "NotConnected", None, message="connection failed")
    rig = make_rig(tmp_path, [lost, failed("sent_known", "ProviderRejected", 400)])
    assert _stop(rig).reason == "ProviderRejected"  # the resent request reached the provider
    assert [r["error_class"] for r in rig.records()] == ["NotConnected", "ProviderRejected"]
    assert rig.sleeps == [5]
    assert rig.budget.spent == Decimal(0) and rig.budget.reserved == Decimal(0)


def test_an_adapter_that_cannot_resend_gets_no_retry(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [failed("sent_unknown", "IdleTimeout", None)])
    rig.adapter.resends = False
    stopped = _stop(rig)
    assert stopped.reason == "IdleTimeout"  # the real class, not a refused retry
    assert len(rig.records()) == 1
    assert rig.budget.stop_reason is not None and "unknown charge" in rig.budget.stop_reason
