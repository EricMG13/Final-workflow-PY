"""S12-C06: the effective accounts of a book are built once, with unchanged lookups."""

from datetime import date

from test_cash_scope import book, cite, line, period

from deploy_vii import statement_validation as sv
from deploy_vii.financial_reconciliation import _account, _balance


def test_repeated_lookups_build_the_account_index_once(monkeypatch) -> None:
    # By hand: three linked lines (two periods, one metric "net_cash_change" with the second line
    # cited as an outflow magnitude, one "revenue" line) give the accounts of
    # statement_accounts, built once however many times the reconciliation asks.
    stmt_items = {m: k for k, m in sv.ACCOUNT_LINKS.items()}
    cfs_capex, is_revenue = stmt_items["net_cash_change"], stmt_items["revenue"]
    periods = (
        period("p1", "FY", None, "FY2024", date(2024, 1, 1), date(2024, 12, 31)),
        period("p2", "FY", None, "FY2025", date(2025, 1, 1), date(2025, 12, 31)),
    )
    lines = (
        line("l1", *cfs_capex, "p1", 7, cite("net cash change 7"), priority=1),
        line("l2", *cfs_capex, "p2", 9, cite("net cash change 9"), priority=2),
        line("l3", *is_revenue, "p1", 100, cite("revenue 100"), priority=3),
    )
    lines = (
        lines[0],
        lines[1].model_copy(update={"sign_convention": "outflow_magnitude"}),
        lines[2],
    )
    b = book().model_copy(update={"periods": periods, "statement_lines": lines, "accounts": ()})
    calls = []
    real = sv.statement_accounts
    monkeypatch.setattr(sv, "statement_accounts", lambda x: calls.append(x) or real(x))
    sv._last_index = None
    assert [sv.account_outflow(b, p, "net_cash_change") for p in ("p1", "p2")] == [False, True]
    assert sv.account_outflow(b, "p2", "revenue") is False
    assert _account(b, "p1", "revenue").amount == 100
    assert _account(b, "p2", "revenue").amount is None
    assert _balance(b, date(2025, 12, 31), "net_cash_change").original_amount == 9
    assert len(calls) == 1
