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
