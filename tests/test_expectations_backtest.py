"""The back-test runs offline on a retained run and reports a verdict per forecast row."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import expectations_backtest as backtest


def test_retained_launcher_run_is_reported_with_verdicts() -> None:
    text = backtest.report(["cpos-launch-live-002"])
    assert "deterministic retained-data report" in text
    assert "TransDigm Group Incorporated, as of 2024-09-30" in text
    assert "| ready (no rule fired) | CP-1 | ready | limited | disagreed |" in text


def test_a_reconstructed_context_case_is_labelled() -> None:
    assert "(reconstructed context)" in backtest.report(["lmi-intercreditor"])


def test_a_module_with_no_handoff_is_read_from_cp0_only_when_cp0_says_blocked() -> None:
    from deploy_workflow import handoff_outcome

    assert handoff_outcome.actual_of("CP-1", None, "CP-0 says CP-1 BLOCKED") == (
        "will_refuse",
        "BLOCKED in CP-0 handoff",
    )
    assert handoff_outcome.actual_of("CP-1", None, "CP-1 READY") == ("not_reached", "no handoff")
    assert handoff_outcome.actual_of("CP-1", None, refused=True) == (
        "will_refuse",
        "run stopped here",
    )
    assert handoff_outcome.actual_of("CP-1", None, "CP-1 READY", refused=True) == (
        "will_refuse",
        "run stopped here",
    )
