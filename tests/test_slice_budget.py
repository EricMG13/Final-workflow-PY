from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from test_model_testing_budget import call, meta

from deploy_workflow.model_testing.budget import AccountExhausted, BudgetError, cap_for
from deploy_workflow.model_testing.records import DurableDebit
from deploy_workflow.model_testing.slice_budget import slice_cap, weekly_spend

NOW = datetime(2026, 11, 4, tzinfo=UTC)


def run(config, amount, run_id, when=NOW):
    return meta(config_id=config, run_id=run_id), (
        call(config, amount, run_id=run_id).model_copy(update={"started_at": when}),
    )


def bound(runs, config="sol-medium"):
    return slice_cap(config, runs, (), cap=Decimal(10), week_cap=Decimal(60), now=NOW)


def test_shared_week_counts_both_providers():
    runs = [run("sol-medium", "30", "sol"), run("opus-medium", "25", "opus")]
    assert bound(runs) == Decimal(5)
    assert bound(runs, "opus-medium") == Decimal(5)
    runs.append(run("opus-medium", "5", "last"))
    with pytest.raises(AccountExhausted, match="shared week"):
        bound(runs)


def test_previous_week_still_reduces_account_capacity():
    runs = [run("sol-medium", "108", "old", NOW - timedelta(days=7))]
    assert weekly_spend(runs, (), NOW) == 0
    assert bound(runs) == min(Decimal(10), cap_for("sol-medium", runs))
    assert bound(runs) < Decimal(10)


def test_unmatched_crash_reservation_counts_across_providers():
    m = meta(config_id="opus-medium", run_id="crash")
    m._durable_debits = (DurableDebit("lost", "opus-medium", Decimal(55), Decimal(55), True),)
    assert bound([(m, ())]) == Decimal(5)


def test_offline_recordings_do_not_spend_weekly_budget():
    m, calls = run("sol-medium", "59", "offline")
    m = meta(mode="offline", run_id="offline")
    assert bound([(m, calls)]) == Decimal(10)


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity"), Decimal(-1), Decimal(0)])
def test_cap_is_finite_and_positive(bad):
    with pytest.raises(BudgetError):
        slice_cap("sol-medium", [], (), cap=bad, week_cap=Decimal(60), now=NOW)
