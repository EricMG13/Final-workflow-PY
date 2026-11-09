"""The run status line never shows a stale spend: run-spend.test.cjs at final-workflow dd3dfa18.

The Node suite lifted showStatus into a vm context with stub elements. Here a launched run is
polled through the real New run screen and the real #run-spend line is read; describeModule is
the page's own global. Synthetic statuses only; no network or provider.
Marked browser: real browser proof.
"""

from __future__ import annotations

from typing import Any

import pytest
from test_issuer_library_app import NewRun

pytestmark = pytest.mark.browser

STALE = {"module": "CP-1", "step": "started", "spent_usd": "0"}


def spend_text(browser: Any, status: dict[str, Any]) -> str:
    run = NewRun(browser, status=status)
    run.launch()
    run.page.wait_for_function("document.getElementById('run-spend').textContent!==''")
    text = run.text("run-spend")
    run.close()
    return text


def test_an_unreadable_ledger_is_shown_as_unreadable_not_as_the_stale_progress_figure(
    browser: Any,
) -> None:
    status = {"state": "failed", "message": "x", "spent_usd": "unknown", "progress": STALE}
    assert spend_text(browser, status) == "Recorded spend could not be read; it may be above zero."


def test_a_recorded_spend_wins_over_progress_and_progress_is_the_fallback_while_running(
    browser: Any,
) -> None:
    stopped = {"state": "stopped", "message": "x", "spent_usd": "7.42", "progress": STALE}
    assert spend_text(browser, stopped) == "Recorded spend: USD 7.42"
    running = {"state": "running", "message": "x", "progress": {**STALE, "spent_usd": "0.10"}}
    assert spend_text(browser, running) == "Recorded spend: USD 0.10"
    assert (
        spend_text(browser, {"state": "running", "message": "x"})
        == "Spend appears after CP-OS records a completed model response."
    )


def test_a_stop_after_every_module_was_accepted_reads_as_a_delivery_stop_not_a_module_stop(
    browser: Any,
) -> None:
    run = NewRun(browser)

    def say(state: str, progress: dict[str, Any]) -> str:
        value: str = run.page.evaluate(
            "([state,progress])=>describeModule({state,progress},['CP-2','CP-6'],id=>'Title '+id)",
            [state, progress],
        )
        return value

    delivering = "stopped while delivering the report"
    assert (
        say(
            "failed",
            {"module": "CP-6", "step": "stopped", "stopped_during": "delivering", "accepted": 2},
        )
        == delivering
    )
    assert say("failed", {"module": "CP-6", "step": "stopped", "accepted": 2}) == delivering
    assert say("failed", {"module": "CP-6", "step": "delivering", "accepted": 2}) == delivering
    assert (
        say("running", {"module": "CP-6", "step": "delivering", "accepted": 2})
        == "delivering the report"
    )
    assert (
        say(
            "failed",
            {"module": "CP-6", "step": "stopped", "stopped_during": "running", "accepted": 1},
        )
        == "stopped during Title CP-6 (2 of 2)"
    )
    run.close()
