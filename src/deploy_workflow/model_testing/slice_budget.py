"""A shared weekly exposure bound over the existing durable account ledger."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from deploy_workflow.model.budget import exact_subtract, exact_sum
from deploy_workflow.model_testing.budget import (
    AccountExhausted,
    BudgetError,
    Runs,
    Settlement,
    require_budget,
    settled_amounts,
)
from deploy_workflow.model_testing.records import call_key


def positive_money(value: Decimal, name: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise BudgetError(f"{name} must be a finite positive Decimal")
    return value


def weekly_spend(runs: Runs, settlements: Sequence[Settlement], now: datetime) -> Decimal:
    """All providers in the UTC ISO week, plus outstanding unmatched marker exposure.

    Undated crash markers carry forward until reconciled; changing week cannot
    release a reservation. Account capacity is calculated separately over all runs.
    """
    if now.tzinfo is None:
        raise BudgetError("weekly accounting requires a timezone-aware clock")
    today = now.astimezone(UTC).date()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=7)
    settled = settled_amounts(runs, settlements)
    amounts: list[Decimal] = []
    for meta, records in runs:
        if meta.mode != "live":
            continue
        amounts.extend(debit.effective_usd for debit in meta.durable_debits)
        for record in records:
            if record.started_at.tzinfo is None:
                raise BudgetError("a recorded call has no timezone")
            if not start <= record.started_at.astimezone(UTC).date() < end:
                continue
            amount = record.settled_usd
            if record.cost_status == "unknown":
                amount = settled.get(call_key(record), record.reserved_usd)
            amounts.append(record.reserved_usd if amount is None else amount)
    return exact_sum(amounts)


def slice_cap(
    config_id: str, runs: Runs, settlements: Sequence[Settlement], *,
    cap: Decimal, week_cap: Decimal, now: datetime,
) -> Decimal:
    """Keep account-wide reconciliation, then apply the run and shared weekly bounds."""
    positive_money(cap, "cap")
    positive_money(week_cap, "week cap")
    account = require_budget(config_id, runs, Decimal(0), settlements)
    remaining = exact_subtract(week_cap, weekly_spend(runs, settlements, now))
    if remaining <= 0:
        raise AccountExhausted(f"shared week cap {week_cap} exhausted")
    result = min(account, cap, remaining)
    if result <= 0:
        raise AccountExhausted(f"{config_id}: account capacity exhausted")
    return result
