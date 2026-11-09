"""S12-A02 (user ruling B, fail closed): a positive `signed` amount on an outflow account is
refused for the model to repair, never flipped to minus its absolute value.

Hand-derived expectations (no production arithmetic): every reader of an outflow account takes
-abs(amount). A source printing "Income taxes refunded (paid), net | 15" recorded `signed` +15
would read -15, wrong by 2 x 15 = 30, so it is refused. The two repairs:
- the source prints the outflow as a positive magnitude: `outflow_magnitude` with `sign_citations`,
  read as -15;
- the source prints a net inflow (a refund): the value is `missing` with a reason, read as missing
  (never 0, never -15, never +15).
Zero is not positive and negative signed amounts are unchanged (-15 stays -15).
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from test_statement_quantities import SHA, book, cite, period

from deploy_vii.contracts import Citation, Run, Source, Span
from deploy_vii.financial_adapter import kernel_registers
from deploy_vii.financial_contracts import (
    AccountObservation,
    Alternative,
    FinancialBook,
    FinancialPeriod,
    FinancialReview,
    Observation,
    StatementLine,
    StatementQuantity,
)
from deploy_vii.financial_reconciliation import Reconciliation, reconcile_financials
from deploy_vii.financial_validation import records, validate_financial_review
from deploy_vii.model import history
from deploy_vii.model._cells import Cell
from deploy_vii.model.history import OUTFLOW_METRICS
from deploy_vii.preparation import PreparedPack
from deploy_vii.statement_extract import ExtractedTable
from deploy_vii.statement_output import StatementCell, statement_report
from deploy_vii.statement_validation import ACCOUNT_LINKS, statement_issues
from deploy_workflow import financial_workflow as fw
from deploy_workflow.statement_lines import line_table

# Every statement item linked to an outflow account, by hand: (statement, item, account).
OUTFLOW_ITEMS = (
    ("IS", "cogs", "cogs"),
    ("IS", "depreciation_amortization", "depreciation_amortization"),
    ("IS", "opex_including_da", "opex_including_da"),
    ("IS", "operating_lease_cost", "operating_lease_cost"),
    ("CFS", "dividends_paid", "dividends_paid"),
    ("CFS", "cash_taxes_paid", "cash_taxes_paid"),
    ("CFS", "cash_interest_paid", "cash_interest_paid"),
    ("CFS", "lease_payments_in_financing", "lease_payments_in_financing"),
    ("CFS", "interest_paid_in_financing", "interest_paid_in_financing"),
    ("CFS", "capex_total", "capex_and_intangible_investment"),
)
REFUND = "Income taxes refunded (paid), net | 15"
WITHHELD = "The source prints a net income tax refund of 15; a refund is not an outflow"
ISSUE = "Positive signed amount on an outflow account"


def observation(oid: str, amount: Decimal | None, quote: str = REFUND) -> Observation:
    if amount is None:
        return Observation(
            observation_id=oid,
            status="missing",
            amount=None,
            citations=(cite(quote),),
            reason=WITHHELD,
        )
    return Observation(observation_id=oid, status="known", amount=amount, citations=(cite(quote),))


def outflow_line(  # noqa: PLR0913 - one keyword per field the cases vary
    statement: str,
    item: str,
    amount: Decimal | None,
    *,
    convention: str = "signed",
    period_id: str = "FY2024",
    line_kind: str = "detail",
    priority: int = 1,
) -> StatementLine:
    line_id = f"{statement.lower()}-{item.replace('_', '-')}"
    return StatementLine(
        line_id=line_id,
        statement=statement,
        item_id=item,
        label=item,
        period_id=period_id,
        display_priority=priority,
        line_kind=line_kind,
        value=observation(f"obs-{line_id}-{period_id}", amount),
        sign_convention=convention,
        sign_citations=(cite(REFUND),) if convention == "outflow_magnitude" else (),
        quantity=StatementQuantity(kind="monetary", scale="MILLIONS", citations=(cite("unit"),)),
    )


def refused(issues: tuple[str, ...]) -> list[str]:
    return [issue for issue in issues if ISSUE in issue]


def test_the_hand_list_is_every_item_linked_to_an_outflow_account() -> None:
    linked = {(s, i, m) for (s, i), m in ACCOUNT_LINKS.items() if m in OUTFLOW_METRICS}
    assert linked == set(OUTFLOW_ITEMS)


@pytest.mark.parametrize(("statement", "item", "account"), OUTFLOW_ITEMS)
def test_a_positive_signed_amount_on_an_outflow_account_is_refused(
    statement: str, item: str, account: str
) -> None:
    row = outflow_line(statement, item, Decimal(15))
    [issue] = refused(statement_issues(book((row,))))
    # The line, its period, the account and both repairs, in one sentence.
    assert f"{row.line_id} FY2024 ({statement} {item}, account {account})" in issue
    assert "`sign_convention: outflow_magnitude` with `sign_citations`" in issue
    assert "net inflow (a refund)" in issue and "status `missing`" in issue
    assert "`reason`" in issue and ". " not in issue


@pytest.mark.parametrize("line_kind", ["subtotal", "total"])
def test_a_positive_signed_subtotal_or_total_on_an_outflow_account_is_refused(
    line_kind: str,
) -> None:
    row = outflow_line("CFS", "capex_total", Decimal("2.5"), line_kind=line_kind)
    assert len(refused(statement_issues(book((row,))))) == 1


@pytest.mark.parametrize(
    "amount",
    [Decimal(0), Decimal("0.00"), Decimal(-15), Decimal("-0.01")],
    ids=["zero", "zero-two-places", "negative", "small-negative"],
)
@pytest.mark.parametrize(("statement", "item", "account"), OUTFLOW_ITEMS)
def test_zero_and_negative_signed_amounts_are_accepted(
    statement: str, item: str, account: str, amount: Decimal
) -> None:
    del account
    assert refused(statement_issues(book((outflow_line(statement, item, amount),)))) == []


@pytest.mark.parametrize(("statement", "item", "account"), OUTFLOW_ITEMS)
def test_a_magnitude_or_a_withheld_refund_is_accepted(
    statement: str, item: str, account: str
) -> None:
    del account
    magnitude = outflow_line(statement, item, Decimal(15), convention="outflow_magnitude")
    withheld = outflow_line(statement, item, None)
    assert refused(statement_issues(book((magnitude,)))) == []
    assert refused(statement_issues(book((withheld,)))) == []


def test_an_outflow_magnitude_without_sign_citations_is_still_refused_by_the_contract() -> None:
    data = outflow_line("CFS", "cash_taxes_paid", Decimal(15)).model_dump()
    data["sign_convention"] = "outflow_magnitude"
    with pytest.raises(ValidationError, match="outflow magnitude normalization requires"):
        StatementLine.model_validate(data)


@pytest.mark.parametrize(
    ("statement", "item"),
    [
        ("IS", "revenue"),  # an inflow account: +15 is a revenue, read +15
        ("CFS", "capex_maintenance"),  # not linked to an account: printed sign kept
        ("CFS", "debt_repayment"),
        ("CFS", "other:income-taxes-refunded-net"),  # issuer detail, not an account
        ("IS", "income_tax_total"),  # linked, but income_tax_expense is not an outflow account
    ],
)
def test_a_positive_signed_amount_off_the_outflow_accounts_is_not_caught(
    statement: str, item: str
) -> None:
    assert refused(statement_issues(book((outflow_line(statement, item, Decimal(15)),)))) == []


@pytest.mark.parametrize(
    "item", ["inventory", "lease_obligations", "total_debt", "other_current_liabilities"]
)
def test_a_balance_sheet_line_is_a_signed_balance_and_not_caught(item: str) -> None:
    bs = period("FY2024-END", 2024).model_copy(
        update={"period_type": "PERIOD_END", "start_date": None, "day_count": None}
    )
    row = outflow_line("BS", item, Decimal(15), period_id="FY2024-END")
    forged = book((row,)).model_copy(update={"periods": (*book().periods, bs)})
    assert refused(statement_issues(forged)) == []


def test_a_conflicting_observation_on_an_outflow_account_is_not_caught() -> None:
    conflict = Observation(
        observation_id="obs-conflict",
        status="conflicting",
        amount=None,
        citations=(cite(REFUND),),
        reason="Two figures are printed",
        alternatives=(
            Alternative(amount=Decimal(15), citations=(cite(REFUND),), explanation="table"),
            Alternative(amount=Decimal(-15), citations=(cite("note"),), explanation="note"),
        ),
    )
    row = outflow_line("CFS", "cash_taxes_paid", None).model_copy(update={"value": conflict})
    assert refused(statement_issues(book((row,)))) == []


# --- end to end: validation, the statement report, the reconciliation and the history/LTM ------

QUARTERS = (
    ("q1-2025", 1, date(2025, 1, 1), date(2025, 3, 31), 90),
    ("q2-2025", 2, date(2025, 4, 1), date(2025, 6, 30), 91),
    ("q3-2025", 3, date(2025, 7, 1), date(2025, 9, 30), 92),
    ("q4-2025", 4, date(2025, 10, 1), date(2025, 12, 31), 92),
)


def quarter(pid: str, number: int, start: date, end: date, days: int) -> FinancialPeriod:
    return period(pid, 2025).model_copy(
        update={
            "period_type": "QUARTER",
            "fiscal_quarter": number,
            "start_date": start,
            "end_date": end,
            "day_count": days,
        }
    )


def flow_book(statement: str, item: str, q2: StatementLine) -> FinancialBook:
    """One outflow item over four calendar 2025 quarters and FY2025: Q1 a printed magnitude 1
    (read -1), Q2 the case, Q3 a printed (1) (signed -1), Q4 zero, FY a printed (2) (signed -2)."""
    fy = period("fy-2025", 2025).model_copy(
        update={"start_date": date(2025, 1, 1), "end_date": date(2025, 12, 31), "day_count": 365}
    )
    lines = (
        outflow_line(
            statement, item, Decimal(1), convention="outflow_magnitude", period_id="q1-2025"
        ),
        q2,
        outflow_line(statement, item, Decimal(-1), period_id="q3-2025"),
        outflow_line(statement, item, Decimal(0), period_id="q4-2025"),
        outflow_line(statement, item, Decimal(-2), period_id="fy-2025"),
    )
    return book(lines).model_copy(update={"periods": (*(quarter(*q) for q in QUARTERS), fy)})


def case(book_value: FinancialBook) -> tuple[PreparedPack, FinancialReview]:
    """A pack whose one source `filing` holds every quote the book cites, and its review."""
    run = Run(
        run_id="signed-outflow",
        issuer_id="issuer",
        issuer_name="Signed Outflow Fixture",
        as_of=date(2026, 6, 30),
        case_kind="synthetic",
    )
    review = FinancialReview(
        pack_sha256=SHA,
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        books=(book_value,),
        analysis=(),
    )
    spans: dict[str, set[str]] = {}
    for citation in records(review, Citation):
        spans.setdefault(citation.locator, set()).add(citation.quote)
    source = Source(
        source_id="filing",
        name="Signed outflow fixture",
        status="ready",
        sha256=SHA,
        spans=tuple(
            Span(locator=locator, text="\n".join(sorted(quotes)))
            for locator, quotes in sorted(spans.items())
        ),
        extraction_status="complete",
    )
    pack = PreparedPack(run=run, sources=(source,))
    return pack, review.model_copy(update={"pack_sha256": pack.content_hash()})


def _downstream(
    statement: str, item: str, account: str, amount: Decimal | None, convention: str = "signed"
) -> tuple[StatementCell, Reconciliation, Cell, Cell]:
    """The Q2 statement cell, the FY_QUARTERS check, the Q2 history cell and the LTM at Q4."""
    q2 = outflow_line(statement, item, amount, convention=convention, period_id="q2-2025")
    pack, review = case(flow_book(statement, item, q2))
    assert validate_financial_review(pack, review) == ()
    cell = next(
        c
        for c in statement_report(pack, review, "book").cells
        if c.item_id == item and c.period_id == "q2-2025"
    )
    check = next(
        c
        for c in reconcile_financials(pack, review, "book").checks
        if c.check_type == "FY_QUARTERS" and c.metric_id == account
    )
    regs = kernel_registers(pack, review, "book")
    columns = history.historical_columns(regs)
    frame = history.account_frame(regs, columns)
    ltm = history.ltm_frames(regs, columns)
    q2_column = next(c.column_id for c in columns if c.period_id == "q2-2025")
    q4_column = next(c.column_id for c in columns if c.period_id == "q4-2025")
    key = f"acct:{account}"
    return cell, check, frame[q2_column][key], ltm[q4_column][key]


@pytest.mark.parametrize(("statement", "item", "account"), OUTFLOW_ITEMS)
def test_a_positive_signed_refund_fails_the_whole_review_closed(
    statement: str, item: str, account: str
) -> None:
    q2 = outflow_line(statement, item, Decimal(15), period_id="q2-2025")
    pack, review = case(flow_book(statement, item, q2))
    [issue] = validate_financial_review(pack, review)
    assert issue.startswith(f"book: {ISSUE}: {q2.line_id} q2-2025 ({statement} {item}, account")
    for build in (statement_report, reconcile_financials, kernel_registers):
        with pytest.raises(ValueError, match=ISSUE):
            build(pack, review, "book")


@pytest.mark.parametrize(("statement", "item", "account"), OUTFLOW_ITEMS)
def test_a_printed_magnitude_is_read_as_the_negative_outflow(
    statement: str, item: str, account: str
) -> None:
    cell, check, q2_cell, ltm_cell = _downstream(
        statement, item, account, Decimal(15), "outflow_magnitude"
    )
    # Source 15 printed as a magnitude: normalized -15.
    assert (cell.source_amount, cell.normalized_amount) == (Decimal(15), Decimal(-15))
    assert cell.normalization == "negative absolute source amount"
    # FY_QUARTERS: Q1 -1, Q2 -15, Q3 -1, Q4 0 sum to -17 against the reported FY -2.
    assert [t.amount for t in check.components] == [-1, -15, -1, 0]
    assert check.calculated_value == Decimal(-17) and check.reported_value == Decimal(-2)
    # History: Q2 reads -15; the LTM at Q4 is -1 - 15 - 1 + 0 = -17.
    assert (q2_cell.value, ltm_cell.value) == (Decimal(-15), Decimal(-17))


@pytest.mark.parametrize(("statement", "item", "account"), OUTFLOW_ITEMS)
def test_a_withheld_refund_is_read_as_missing_downstream(
    statement: str, item: str, account: str
) -> None:
    cell, check, q2_cell, ltm_cell = _downstream(statement, item, account, None)
    # Statement report: missing, no source or normalized figure, the reason as the limitation.
    assert (cell.status, cell.source_amount, cell.normalized_amount) == ("missing", None, None)
    assert (cell.normalization, cell.limitation) == ("identity", WITHHELD)
    # Reconciliation: the Q2 term has no amount (never 0, -15 or +15) and carries the reason, so
    # the quarters do not sum.
    q2_term = check.components[1]
    assert (q2_term.original_amount, q2_term.amount, q2_term.reason) == (None, None, WITHHELD)
    assert check.calculated_value is None and check.status == "BLOCK"
    # History and LTM: Q2 has no figure; the LTM at Q4 cannot be summed.
    assert q2_cell.value is None and q2_cell.reason == "NOT_STATED"
    assert ltm_cell.value is None and ltm_cell.reason == "COMPONENT_MISSING"


@pytest.mark.parametrize(("statement", "item", "account"), OUTFLOW_ITEMS)
def test_zero_and_a_negative_signed_amount_read_unchanged_downstream(
    statement: str, item: str, account: str
) -> None:
    zero_cell, zero_check, zero_q2, zero_ltm = _downstream(statement, item, account, Decimal(0))
    # Zero is not positive: no normalization; Q1 -1, Q2 0, Q3 -1, Q4 0 = -2, the reported FY.
    assert (zero_cell.normalization, zero_q2.value, zero_ltm.value) == ("identity", 0, -2)
    assert zero_check.calculated_value == Decimal(-2)
    cell, check, q2_cell, ltm_cell = _downstream(statement, item, account, Decimal(-15))
    # -15 printed as (15): unchanged, no normalization; Q1 -1, Q2 -15, Q3 -1, Q4 0 = -17.
    assert (cell.source_amount, cell.normalized_amount) == (Decimal(-15), Decimal(-15))
    assert cell.normalization == "identity"
    assert check.calculated_value == Decimal(-17)
    assert (q2_cell.value, ltm_cell.value) == (Decimal(-15), Decimal(-17))


# --- the live coverage gate: a withheld refund row written by hand -------------------------------
# The CFS unit prints "Income taxes refunded (paid), net  (1)  15  (1)  0  13": Q1 and Q3 paid 1
# (signed -1), Q2 a net refund of 15 and FY a net refund of 13 (-1 + 15 - 1 + 0 = 13), Q4 nil 0.
# The two refunds are withheld as `missing` with a reason; the gate expects the printed amount
# otherwise, so a missing line on the -1 or the 0 column, or without a reason, stays uncovered.

ROW = "Income taxes refunded (paid), net"
UNIT = (
    "CONSOLIDATED CASH FLOW STATEMENT",
    "Period  Q1 2025  Q2 2025  Q3 2025  Q4 2025  FY 2025",
    f"{ROW}  (1)  15  (1)  0  13",
)
PRINTED = {"q1-2025": -1, "q2-2025": 15, "q3-2025": -1, "q4-2025": 0, "fy-2025": 13}


def unit_table() -> ExtractedTable:
    spans = {n: Span(locator=f"line:{n}", text=text) for n, text in enumerate(UNIT, 1)}
    return line_table(spans, "line:1-3", "filing")


def row_line(
    period_id: str, observation: Observation, item: str = "cash_taxes_paid"
) -> StatementLine:
    return StatementLine(
        line_id="cfs-income-taxes-refunded-paid-net",
        statement="CFS",
        item_id=item,
        label=ROW,
        period_id=period_id,
        display_priority=1,
        line_kind="detail",
        value=observation,
        quantity=None,
    )


def row_value(period_id: str, withheld: frozenset[str]) -> Observation:
    citation = (cite(ROW, locator="line:3"),)
    if period_id in withheld:
        return Observation(
            observation_id=f"tax-{period_id}",
            status="missing",
            amount=None,
            citations=citation,
            reason=WITHHELD,
        )
    return Observation(
        observation_id=f"tax-{period_id}",
        status="known",
        amount=Decimal(PRINTED[period_id]),
        citations=citation,
    )


def refund_book(
    withheld: frozenset[str] = frozenset({"q2-2025", "fy-2025"}),
    item: str = "cash_taxes_paid",
    replace: dict[str, Observation] | None = None,
) -> FinancialBook:
    fy = period("fy-2025", 2025).model_copy(
        update={"start_date": date(2025, 1, 1), "end_date": date(2025, 12, 31), "day_count": 365}
    )
    lines = tuple(
        row_line(pid, (replace or {}).get(pid) or row_value(pid, withheld), item) for pid in PRINTED
    )
    return book(lines).model_copy(update={"periods": (*(quarter(*q) for q in QUARTERS), fy)})


def gate(book_value: FinancialBook) -> str | None:
    table = unit_table()
    [row] = table.lines
    return fw._uncovered_reason(table, row, "CFS", (book_value,))


def test_the_unit_prints_the_refund_row_as_described() -> None:
    [row] = unit_table().lines
    assert (row.locator, row.label, row.values) == ("line:3", ROW, (-1, 15, -1, 0, 13))


def test_a_withheld_refund_row_passes_the_coverage_gate_and_reads_missing_downstream() -> None:
    refund = refund_book()
    assert gate(refund) is None
    pack, review = case(refund)
    assert validate_financial_review(pack, review) == ()
    cells = {
        c.period_id: c
        for c in statement_report(pack, review, "book").cells
        if c.item_id == "cash_taxes_paid"
    }
    assert (cells["q2-2025"].status, cells["q2-2025"].normalized_amount) == ("missing", None)
    assert cells["q2-2025"].limitation == WITHHELD
    assert cells["q1-2025"].normalized_amount == Decimal(-1)
    check = next(
        c
        for c in reconcile_financials(pack, review, "book").checks
        if c.check_type == "FY_QUARTERS" and c.metric_id == "cash_taxes_paid"
    )
    # The FY refund and the Q2 refund are withheld: no reported value, Q2 term None with reason.
    assert (check.reported_value, check.calculated_value, check.status) == (None, None, "BLOCK")
    assert [t.amount for t in check.components] == [-1, None, -1, 0]
    assert check.components[1].reason == WITHHELD
    regs = kernel_registers(pack, review, "book")
    columns = history.historical_columns(regs)
    frame = history.account_frame(regs, columns)
    ltm = history.ltm_frames(regs, columns)
    column = {c.period_id: c.column_id for c in columns}
    q2 = frame[column["q2-2025"]]["acct:cash_taxes_paid"]
    assert (q2.value, q2.reason) == (None, "NOT_STATED")
    q4_ltm = ltm[column["q4-2025"]]["acct:cash_taxes_paid"]
    assert (q4_ltm.value, q4_ltm.reason) == (None, "COMPONENT_MISSING")


@pytest.mark.parametrize(
    ("period_id", "printed"), [("q1-2025", "-1"), ("q3-2025", "-1"), ("q4-2025", "0")]
)
def test_a_missing_line_on_a_negative_or_zero_cell_is_still_uncovered(
    period_id: str, printed: str
) -> None:
    reason = gate(refund_book(frozenset({"q2-2025", "fy-2025", period_id})))
    assert reason == f"amount: {period_id} expects {printed}"


def test_a_missing_line_without_a_reason_is_refused() -> None:
    with pytest.raises(ValidationError, match="unsettled observation requires null amount"):
        Observation(observation_id="x", status="missing", amount=None, citations=(cite(ROW),))
    # A line that bypassed the contract is still not a withheld refund for the gate.
    bare = Observation.model_construct(
        observation_id="tax-q2-2025",
        status="missing",
        amount=None,
        citations=(cite(ROW, locator="line:3"),),
        reason=None,
        alternatives=(),
    )
    full = refund_book()
    lines = tuple(
        line.model_copy(update={"value": bare}) if line.period_id == "q2-2025" else line
        for line in full.statement_lines
    )
    assert gate(full.model_copy(update={"statement_lines": lines})) == "amount: q2-2025 expects 15"


@pytest.mark.parametrize(
    "item", ["other:income-taxes-refunded-paid-net", "debt_repayment", "capex_maintenance"]
)
def test_a_missing_line_off_the_outflow_accounts_is_still_uncovered(item: str) -> None:
    assert gate(refund_book(item=item)) == "amount: q2-2025 expects 15"


def test_a_not_applicable_refund_is_still_uncovered() -> None:
    other = Observation(
        observation_id="tax-q2-2025",
        status="not_applicable",
        amount=None,
        citations=(cite(ROW, locator="line:3"),),
        reason=WITHHELD,
    )
    assert gate(refund_book(replace={"q2-2025": other})) == "amount: q2-2025 expects 15"


def test_a_signed_refund_is_covered_by_the_gate_but_refused_by_validation() -> None:
    signed = refund_book(withheld=frozenset())
    assert gate(signed) is None
    assert len(refused(statement_issues(signed))) == 2  # Q2 +15 and FY +13


# --- confidence review (second model): adversarial cases, hand-derived expectations ---------------


@pytest.mark.parametrize("amount", [Decimal("0.000000001"), Decimal("1E+17")], ids=["tiny", "huge"])
def test_any_positive_signed_amount_is_refused_however_small_or_large(amount: Decimal) -> None:
    # Positive is the only test: no tolerance, no rounding to zero.
    assert len(refused(statement_issues(book((outflow_line("CFS", "capex_total", amount),))))) == 1


def test_one_issue_per_offending_line_and_none_for_the_clean_neighbours() -> None:
    # Five periods of cash_taxes_paid: +1 (Q1), -1 (Q2), 0 (Q3), +2 (Q4), a printed magnitude 3
    # (FY). By hand the offending lines are Q1 and Q4: two issues, one naming each period.
    pids = ("q1-2025", "q2-2025", "q3-2025", "q4-2025", "fy-2025")
    amounts = (Decimal(1), Decimal(-1), Decimal(0), Decimal(2), Decimal(3))
    lines = tuple(
        outflow_line(
            "CFS",
            "cash_taxes_paid",
            amount,
            convention="outflow_magnitude" if pid == "fy-2025" else "signed",
            period_id=pid,
        )
        for pid, amount in zip(pids, amounts, strict=True)
    )
    forged = flow_book("CFS", "cash_taxes_paid", lines[1]).model_copy(
        update={"statement_lines": lines}
    )
    found = refused(statement_issues(forged))
    assert len(found) == 2
    assert " q1-2025 (" in found[0] and " q4-2025 (" in found[1]


def test_an_explicit_account_that_agrees_with_the_flip_no_longer_hides_the_refund() -> None:
    # The pre-fix blind spot: account cash_taxes_paid -15 and a signed +15 line normalise to the
    # same -15, so no disagreement was raised. The +15 line is now refused on its own.
    account = AccountObservation(
        metric_id="cash_taxes_paid", period_id="FY2024", value=observation("acct-tax", Decimal(-15))
    )
    row = outflow_line("CFS", "cash_taxes_paid", Decimal(15))
    forged = book((row,)).model_copy(update={"accounts": (account,)})
    assert len(refused(statement_issues(forged))) == 1


def test_an_explicit_account_row_keeps_its_documented_magnitude_reading() -> None:
    # book.accounts rows are untouched by the ruling: +15 on an outflow account stays accepted and
    # is read -15 (history.OUTFLOW_METRICS).
    account = AccountObservation(
        metric_id="cash_taxes_paid", period_id="FY2024", value=observation("acct-tax", Decimal(15))
    )
    forged = book().model_copy(update={"accounts": (account,)})
    assert statement_issues(forged) == ()


IS_UNIT = (
    "CONSOLIDATED INCOME STATEMENT",
    "Period  Q1 2025  Q2 2025",
    "Cost of sales  15  15",
)


def _cost_of_sales_book(*, withheld: bool, cites_row: bool) -> FinancialBook:
    locator = "line:3" if cites_row else "line:2"
    lines = tuple(
        StatementLine(
            line_id="is-cost-of-sales",
            statement="IS",
            item_id="cogs",
            label="Cost of sales",
            period_id=pid,
            display_priority=1,
            line_kind="detail",
            value=Observation(
                observation_id=f"cogs-{pid}",
                status="missing",
                amount=None,
                citations=(cite("Cost of sales", locator=locator),),
                reason="withheld",
            )
            if withheld
            else Observation(
                observation_id=f"cogs-{pid}",
                status="known",
                amount=Decimal(15),
                citations=(cite("Cost of sales", locator=locator),),
            ),
            quantity=None,
        )
        for pid in ("q1-2025", "q2-2025")
    )
    return book(lines).model_copy(update={"periods": tuple(quarter(*q) for q in QUARTERS[:2])})


def test_an_ordinary_printed_outflow_can_be_withheld_but_only_as_a_missing_value() -> None:
    # Accepted breadth, stated: the gate cannot tell a refund from a printed magnitude, so a model
    # may withhold "Cost of sales 15 15". Hand-derived consequence: the value is lost, the report
    # reads it missing (never 0, 15 or -15) and the reason is kept.
    table = line_table(
        {n: Span(locator=f"line:{n}", text=t) for n, t in enumerate(IS_UNIT, 1)},
        "line:1-3",
        "filing",
    )
    [row] = table.lines
    held = _cost_of_sales_book(withheld=True, cites_row=True)
    assert fw._uncovered_reason(table, row, "IS", (held,)) is None
    pack, review = case(held)
    assert validate_financial_review(pack, review) == ()
    cells = [c for c in statement_report(pack, review, "book").cells if c.item_id == "cogs"]
    assert {c.period_id: (c.status, c.source_amount, c.normalized_amount) for c in cells} == {
        "q1-2025": ("missing", None, None),
        "q2-2025": ("missing", None, None),
    }
    assert {c.limitation for c in cells} == {"withheld"}


def test_a_withheld_outflow_must_still_cite_its_row() -> None:
    # The relaxation is the amount check only: a missing line that does not cite the unit's own
    # row (line:3) is still uncovered, as a period failure.
    table = line_table(
        {n: Span(locator=f"line:{n}", text=t) for n, t in enumerate(IS_UNIT, 1)},
        "line:1-3",
        "filing",
    )
    [row] = table.lines
    elsewhere = _cost_of_sales_book(withheld=True, cites_row=False)
    reason = fw._uncovered_reason(table, row, "IS", (elsewhere,))
    assert reason is not None and reason.startswith("period: no IS line")


# --- user ruling: `outflow_magnitude` is refused on a label that states an inflow -----------------
# Hand-derived: `outflow_magnitude` is read -abs(amount). "Income taxes refunded | 15" kept as a
# magnitude would read -15 where the source prints a refund of +15 (wrong by 30), and a refund
# printed (15) under `outflow_magnitude` reads -15 by the convention, not by the printed sign. So
# the convention is refused on an outflow-linked line whose label states an inflow, whatever the
# amount. The inflow words, written here by hand from the ruling: refund(s|ed), received,
# receipt(s), proceeds, inflow(s), reimbursement(s); a word inside a "net of" clause states no
# inflow ("Cash taxes paid, net of refunds received" is an outflow net of refunds).

INFLOW_ISSUE = "Outflow magnitude on a label that states an inflow"
INFLOW_LABELS = (
    ("Income tax refund", "refund"),
    ("Refunds of taxes paid", "refunds"),
    ("Income taxes refunded (paid), net", "refunded"),
    ("Interest received", "received"),
    ("Tax receipt", "receipt"),
    ("Receipts (payments) of income taxes", "receipts"),
    ("Proceeds from sale of PP&E", "proceeds"),
    ("Cash inflow from grants", "inflow"),
    ("Inflows from tax credits", "inflows"),
    ("Insurance reimbursement", "reimbursement"),
    ("Reimbursements of lease payments", "reimbursements"),
)
# Retained labels the scan of cases/ and runs/ found (statement-coverage, TDG FY2024 10-K
# supplemental, TDG peers) and the "net of" forms the confidence review tried: all outflows.
NET_OF_LABELS = (
    "Cash taxes paid, net of refunds received",
    "Cash paid during the period for income taxes, net of tax refunds received",
    "Cash paid during the period for income taxes, net of refunds",
    "Income taxes paid, net of refunds",
    "capex, net of proceeds",
    "CAPEX, NET OF PROCEEDS",
    "Cash taxes paid (net of refunds received)",
    "Taxes paid net of refunds",
    "Taxes paid （net of refunds）",
    "Purchase of PP&E, net of proceeds (note 12)",
    "Purchase of PP&E [net of proceeds]",
    "Capex, net-of proceeds",
    "Taxes paid, net of (refunds) received",
    "Net of refunds, taxes paid",
    "Imp\u00f4ts pay\u00e9s ; net of refunds",
    "Taxes paid \u2013 net of refunds",
    "Taxes paid \u00abnet of refunds\u00bb",
)
# Labels with no inflow word at all (a receivable is not a receipt, refundable is not a refund).
PLAIN_LABELS = ("Cash tax paid", "Total capital expenditure", "Receivables", "Refundable advances")


def labelled(  # noqa: PLR0913 - one keyword per field the cases vary
    label: str,
    amount: Decimal | None = Decimal(15),
    *,
    statement: str = "CFS",
    item: str = "cash_taxes_paid",
    convention: str = "outflow_magnitude",
    period_id: str = "FY2024",
) -> StatementLine:
    line = outflow_line(statement, item, amount, convention=convention, period_id=period_id)
    return line.model_copy(update={"label": label})


def inflow_refused(issues: tuple[str, ...]) -> list[str]:
    return [issue for issue in issues if INFLOW_ISSUE in issue]


@pytest.mark.parametrize(("label", "word"), INFLOW_LABELS)
def test_each_inflow_word_refuses_an_outflow_magnitude(label: str, word: str) -> None:
    row = labelled(label)
    [issue] = inflow_refused(statement_issues(book((row,))))
    # The line, its period, the account, the word and both repairs, in one sentence.
    assert f"{row.line_id} FY2024 (CFS cash_taxes_paid, account cash_taxes_paid" in issue
    assert f'label word "{word}"' in issue
    assert "`sign_convention: signed` with the negative amount" in issue
    assert "net inflow (a refund)" in issue and "status `missing`" in issue
    assert "`reason`" in issue and ". " not in issue


@pytest.mark.parametrize(("statement", "item", "account"), OUTFLOW_ITEMS)
def test_every_outflow_account_refuses_an_inflow_label_magnitude(
    statement: str, item: str, account: str
) -> None:
    row = labelled("Income taxes refunded", statement=statement, item=item)
    [issue] = inflow_refused(statement_issues(book((row,))))
    assert f'({statement} {item}, account {account}, label word "refunded")' in issue


@pytest.mark.parametrize(
    "amount", [Decimal(15), Decimal(-15), Decimal(0)], ids=["positive", "negative", "zero"]
)
def test_the_refusal_does_not_depend_on_the_amount(amount: Decimal) -> None:
    # -15 under outflow_magnitude also reads -15 by the convention: refused all the same.
    assert len(inflow_refused(statement_issues(book((labelled("Tax refund", amount),))))) == 1


@pytest.mark.parametrize("label", NET_OF_LABELS)
def test_an_inflow_word_inside_a_net_of_clause_keeps_the_magnitude(label: str) -> None:
    for statement, item, _ in OUTFLOW_ITEMS:
        row = labelled(label, statement=statement, item=item)
        assert statement_issues(book((row,))) == (), (label, item)


@pytest.mark.parametrize(
    ("label", "word"),
    [
        ("Cash taxes paid (net of refunds) and refunds received", "refunds"),
        ("Taxes paid, net of refunds; receipts of grants", "receipts"),
        ("Taxes paid （net of refunds） and receipts", "receipts"),
        ("Proceeds, net of capex", "proceeds"),
        ("INCOME TAXES REFUNDED", "refunded"),
        ("Income tax REFUNDS", "refunds"),
        ("Tax-refunds", "refunds"),
        ("Income taxes paid (refunded)", "refunded"),
        ("Taxes paid, net of refunds\uff1b receipts of grants", "receipts"),
        ("Refunds received, net of taxes paid", "refunds"),
    ],
)
def test_an_inflow_word_outside_the_clause_still_refuses(label: str, word: str) -> None:
    [issue] = inflow_refused(statement_issues(book((labelled(label),))))
    assert f'label word "{word}"' in issue


def test_proceeds_on_a_capex_line_is_refused_and_capex_net_of_proceeds_is_kept() -> None:
    proceeds = labelled("Proceeds from sale of PP&E", statement="CFS", item="capex_total")
    [issue] = inflow_refused(statement_issues(book((proceeds,))))
    assert "(CFS capex_total, account capex_and_intangible_investment" in issue
    net = labelled("Capex, net of proceeds", statement="CFS", item="capex_total")
    assert statement_issues(book((net,))) == ()


@pytest.mark.parametrize("label", PLAIN_LABELS)
def test_a_label_without_an_inflow_word_keeps_the_magnitude(label: str) -> None:
    assert statement_issues(book((labelled(label),))) == ()


@pytest.mark.parametrize("label", [label for label, _ in INFLOW_LABELS])
def test_a_signed_negative_or_a_missing_refund_label_is_accepted(label: str) -> None:
    negative = labelled(label, Decimal(-15), convention="signed")
    withheld = labelled(label, None, convention="signed")
    assert statement_issues(book((negative,))) == ()
    assert statement_issues(book((withheld,))) == ()


def test_a_positive_signed_refund_label_gets_the_signed_outflow_issue_only() -> None:
    issues = statement_issues(book((labelled("Tax refund", convention="signed"),)))
    assert len(refused(issues)) == 1 and inflow_refused(issues) == []


@pytest.mark.parametrize(
    ("statement", "item"),
    [
        ("IS", "revenue"),
        ("CFS", "capex_maintenance"),
        ("CFS", "other:income-taxes-refunded"),
        ("IS", "income_tax_total"),
    ],
)
def test_an_inflow_label_magnitude_off_the_outflow_accounts_is_not_caught(
    statement: str, item: str
) -> None:
    row = labelled("Income taxes refunded", statement=statement, item=item)
    assert inflow_refused(statement_issues(book((row,)))) == []


def test_one_issue_per_offending_period() -> None:
    # One refund line over FY2024 and FY2023, both kept as magnitudes: two issues, one a period.
    lines = tuple(labelled("Tax refunds", period_id=pid) for pid in ("FY2024", "FY2023"))
    found = inflow_refused(statement_issues(book(lines)))
    assert len(found) == 2
    assert " FY2024 (" in found[0] and " FY2023 (" in found[1]


def _relabelled(label: str, q2: StatementLine) -> tuple[PreparedPack, FinancialReview]:
    """`flow_book` for cash_taxes_paid with every period's line under one label."""
    full = flow_book("CFS", "cash_taxes_paid", q2)
    lines = tuple(line.model_copy(update={"label": label}) for line in full.statement_lines)
    return case(full.model_copy(update={"statement_lines": lines}))


def test_an_inflow_label_magnitude_fails_the_whole_review_closed() -> None:
    q2 = labelled("Income taxes refunded", period_id="q2-2025")
    pack, review = _relabelled("Income taxes refunded", q2)
    issues = validate_financial_review(pack, review)
    # Q1 carries a magnitude too (flow_book: Q1 printed magnitude 1); Q3, Q4, FY are signed.
    assert [i.split(" (")[0] for i in issues] == [
        f"book: {INFLOW_ISSUE}: cfs-cash-taxes-paid q1-2025",
        f"book: {INFLOW_ISSUE}: cfs-cash-taxes-paid q2-2025",
    ]
    for build in (statement_report, reconcile_financials, kernel_registers):
        with pytest.raises(ValueError, match=INFLOW_ISSUE):
            build(pack, review, "book")


@pytest.mark.parametrize(
    ("label", "convention", "amount", "q2_value", "ltm_value"),
    [
        # A net-of label kept as a magnitude 15: read -15; LTM at Q4 -1 - 15 - 1 + 0 = -17.
        ("Cash taxes paid, net of refunds received", "outflow_magnitude", 15, -15, -17),
        # A refund label printed (15), signed: read -15 unchanged; LTM -17.
        ("Income taxes refunded (paid), net", "signed", -15, -15, -17),
    ],
)
def test_valid_refund_and_net_of_labels_read_unchanged_downstream(
    label: str, convention: str, amount: int, q2_value: int, ltm_value: int
) -> None:
    q1 = labelled(label, Decimal(1), period_id="q1-2025")
    if convention == "signed":
        q1 = labelled(label, Decimal(-1), convention="signed", period_id="q1-2025")
    q2 = labelled(label, Decimal(amount), convention=convention, period_id="q2-2025")
    full = flow_book("CFS", "cash_taxes_paid", q2)
    lines = tuple(
        q1 if line.period_id == "q1-2025" else line.model_copy(update={"label": label})
        for line in full.statement_lines
    )
    pack, review = case(full.model_copy(update={"statement_lines": lines}))
    assert validate_financial_review(pack, review) == ()
    regs = kernel_registers(pack, review, "book")
    columns = history.historical_columns(regs)
    frame = history.account_frame(regs, columns)
    ltm = history.ltm_frames(regs, columns)
    column = {c.period_id: c.column_id for c in columns}
    assert frame[column["q2-2025"]]["acct:cash_taxes_paid"].value == Decimal(q2_value)
    assert ltm[column["q4-2025"]]["acct:cash_taxes_paid"].value == Decimal(ltm_value)
    cell = next(
        c
        for c in statement_report(pack, review, "book").cells
        if c.item_id == "cash_taxes_paid" and c.period_id == "q2-2025"
    )
    assert (cell.source_amount, cell.normalized_amount) == (Decimal(amount), Decimal(q2_value))


def test_a_withheld_refund_label_reads_missing_downstream() -> None:
    label = "Income taxes refunded (paid), net"
    q1 = labelled(label, Decimal(-1), convention="signed", period_id="q1-2025")
    q2 = labelled(label, None, convention="signed", period_id="q2-2025")
    full = flow_book("CFS", "cash_taxes_paid", q2)
    lines = tuple(
        q1 if line.period_id == "q1-2025" else line.model_copy(update={"label": label})
        for line in full.statement_lines
    )
    pack, review = case(full.model_copy(update={"statement_lines": lines}))
    assert validate_financial_review(pack, review) == ()
    regs = kernel_registers(pack, review, "book")
    columns = history.historical_columns(regs)
    frame = history.account_frame(regs, columns)
    column = {c.period_id: c.column_id for c in columns}
    q2_cell = frame[column["q2-2025"]]["acct:cash_taxes_paid"]
    # Missing, never 0, -15 or +15.
    assert (q2_cell.value, q2_cell.reason) == (None, "NOT_STATED")


# --- user ruling: an accounts row cannot contradict a withheld refund -----------------------------
# Hand-derived: a `book.accounts` row takes precedence over the statement (`effective_accounts`) and
# an outflow account's row is read -abs(amount). Beside a statement line withheld as `missing` (a
# net refund of 15), an account written +15 would read -15 in a period the statement withholds:
# wrong by 30 against the printed refund, and a figure where the register should hold none. So any
# account amount (+15, -15 or 0) beside a withheld line of its account and period is a conflict; a
# null account amount (`missing` or `conflicting`) or no account row agrees with the withheld line.

CONFLICT_ISSUE = "Account contradicts a withheld statement line"


def account(metric: str, amount: Decimal | None, period_id: str = "FY2024") -> AccountObservation:
    return AccountObservation(
        metric_id=metric,
        period_id=period_id,
        value=observation(f"acct-{metric}-{period_id}", amount),
    )


def with_accounts(lines: tuple[StatementLine, ...], *rows: AccountObservation) -> FinancialBook:
    return book(lines).model_copy(update={"accounts": rows})


def conflicts(issues: tuple[str, ...]) -> list[str]:
    return [issue for issue in issues if CONFLICT_ISSUE in issue]


@pytest.mark.parametrize(("statement", "item", "account_id"), OUTFLOW_ITEMS)
def test_an_account_amount_beside_a_withheld_line_is_refused(
    statement: str, item: str, account_id: str
) -> None:
    line = outflow_line(statement, item, None)
    forged = with_accounts((line,), account(account_id, Decimal(15)))
    [issue] = conflicts(statement_issues(forged))
    # The account, the period and the line, and the repair, in one sentence.
    assert f"account {account_id} FY2024 carries an amount while {line.line_id}" in issue
    assert f"({statement} {item}) is withheld as `missing`" in issue
    assert "leave that account row out or give it a null `amount`" in issue
    assert ". " not in issue


@pytest.mark.parametrize(
    "amount", [Decimal(15), Decimal(-15), Decimal(0)], ids=["positive", "negative", "zero"]
)
def test_any_account_figure_beside_a_withheld_line_is_refused(amount: Decimal) -> None:
    # 0 is a figure, not a gap: a zero account beside a withheld refund still contradicts it.
    line = outflow_line("CFS", "cash_taxes_paid", None)
    forged = with_accounts((line,), account("cash_taxes_paid", amount))
    assert len(conflicts(statement_issues(forged))) == 1


def test_a_null_account_beside_a_withheld_line_is_accepted() -> None:
    line = outflow_line("CFS", "cash_taxes_paid", None)
    missing = account("cash_taxes_paid", None)
    conflicting = AccountObservation(
        metric_id="cash_taxes_paid",
        period_id="FY2024",
        value=Observation(
            observation_id="acct-conflict",
            status="conflicting",
            amount=None,
            citations=(cite(REFUND),),
            reason="Two figures are printed",
            alternatives=(
                Alternative(amount=Decimal(15), citations=(cite(REFUND),), explanation="table"),
                Alternative(amount=Decimal(-15), citations=(cite("note"),), explanation="note"),
            ),
        ),
    )
    assert statement_issues(with_accounts((line,), missing)) == ()
    assert statement_issues(with_accounts((line,), conflicting)) == ()
    assert statement_issues(with_accounts((line,))) == ()


@pytest.mark.parametrize(
    ("line_amount", "convention", "account_amount"),
    [
        (Decimal(-15), "signed", Decimal(15)),  # both read -15: agree
        (Decimal(-15), "signed", Decimal(-15)),
        (Decimal(15), "outflow_magnitude", Decimal(15)),  # magnitude 15 reads -15: agree
        (Decimal(0), "signed", Decimal(0)),
    ],
)
def test_an_account_beside_a_known_line_is_unchanged(
    line_amount: Decimal, convention: str, account_amount: Decimal
) -> None:
    line = outflow_line("CFS", "cash_taxes_paid", line_amount, convention=convention)
    assert (
        statement_issues(with_accounts((line,), account("cash_taxes_paid", account_amount))) == ()
    )


def test_an_account_beside_a_known_line_that_disagrees_keeps_the_existing_issue() -> None:
    # Line -15, account -16: the existing disagreement issue, not the withheld-line conflict.
    line = outflow_line("CFS", "cash_taxes_paid", Decimal(-15))
    issues = statement_issues(with_accounts((line,), account("cash_taxes_paid", Decimal(-16))))
    assert issues == (
        "Statement/account disagreement requires explicit conflict: cash_taxes_paid FY2024",
    )


def test_an_account_in_another_period_than_the_withheld_line_is_unchanged() -> None:
    # FY2024 withheld, account for FY2023 with no FY2023 line: nothing to contradict.
    line = outflow_line("CFS", "cash_taxes_paid", None)
    assert (
        statement_issues(with_accounts((line,), account("cash_taxes_paid", Decimal(15), "FY2023")))
        == ()
    )


def test_another_accounts_metric_beside_a_withheld_line_is_unchanged() -> None:
    # The withheld line is cash_taxes_paid; the account is cash_interest_paid: no link.
    line = outflow_line("CFS", "cash_taxes_paid", None)
    forged = with_accounts((line,), account("cash_interest_paid", Decimal(15)))
    assert statement_issues(forged) == ()


@pytest.mark.parametrize(
    ("statement", "item", "metric"),
    [("IS", "revenue", "revenue"), ("IS", "income_tax_total", "income_tax_expense")],
)
def test_a_withheld_line_of_an_account_that_is_not_an_outflow_is_not_caught(
    statement: str, item: str, metric: str
) -> None:
    # Outside the ruling: a non-outflow account is read as written, so no sign is invented.
    line = outflow_line(statement, item, None)
    assert conflicts(statement_issues(with_accounts((line,), account(metric, Decimal(15))))) == []


def _accounts_case(q2_account: AccountObservation | None) -> tuple[PreparedPack, FinancialReview]:
    """`flow_book` for cash_taxes_paid with Q2 withheld and, optionally, a Q2 accounts row."""
    q2 = outflow_line("CFS", "cash_taxes_paid", None, period_id="q2-2025")
    full = flow_book("CFS", "cash_taxes_paid", q2)
    rows = () if q2_account is None else (q2_account,)
    return case(full.model_copy(update={"accounts": rows}))


def test_an_account_beside_a_withheld_refund_fails_the_whole_review_closed() -> None:
    pack, review = _accounts_case(account("cash_taxes_paid", Decimal(15), "q2-2025"))
    [issue] = validate_financial_review(pack, review)
    assert issue.startswith(
        f"book: {CONFLICT_ISSUE}: account cash_taxes_paid q2-2025 carries an amount while "
        "cfs-cash-taxes-paid (CFS cash_taxes_paid)"
    )
    for build in (statement_report, reconcile_financials, kernel_registers):
        with pytest.raises(ValueError, match=CONFLICT_ISSUE):
            build(pack, review, "book")


@pytest.mark.parametrize("repair", ["missing", "absent"])
def test_a_repaired_account_reads_the_withheld_refund_as_missing(repair: str) -> None:
    row = account("cash_taxes_paid", None, "q2-2025") if repair == "missing" else None
    pack, review = _accounts_case(row)
    assert validate_financial_review(pack, review) == ()
    regs = kernel_registers(pack, review, "book")
    columns = history.historical_columns(regs)
    frame = history.account_frame(regs, columns)
    ltm = history.ltm_frames(regs, columns)
    column = {c.period_id: c.column_id for c in columns}
    q2 = frame[column["q2-2025"]]["acct:cash_taxes_paid"]
    # Q2 has no figure (never 0, -15 or +15), so the LTM at Q4 cannot be summed.
    assert q2.value is None
    assert ltm[column["q4-2025"]]["acct:cash_taxes_paid"].value is None


def test_an_account_beside_a_known_line_reads_unchanged_end_to_end() -> None:
    # Q2 line signed -15 and a Q2 account +15: both read -15. Q1 -1, Q2 -15, Q3 -1, Q4 0: LTM -17.
    q2 = outflow_line("CFS", "cash_taxes_paid", Decimal(-15), period_id="q2-2025")
    full = flow_book("CFS", "cash_taxes_paid", q2)
    acct = account("cash_taxes_paid", Decimal(15), "q2-2025")
    pack, review = case(full.model_copy(update={"accounts": (acct,)}))
    assert validate_financial_review(pack, review) == ()
    regs = kernel_registers(pack, review, "book")
    columns = history.historical_columns(regs)
    frame = history.account_frame(regs, columns)
    ltm = history.ltm_frames(regs, columns)
    column = {c.period_id: c.column_id for c in columns}
    assert frame[column["q2-2025"]]["acct:cash_taxes_paid"].value == Decimal(-15)
    assert ltm[column["q4-2025"]]["acct:cash_taxes_paid"].value == Decimal(-17)


# --- review of the two refund-sign rulings: adversarial cases (hand-derived) ----------------------
# A "net of" clause ends at the bracket that encloses it, at a semicolon or at the label's end; a
# bracketed part inside it stays in it (one level of nesting); an unbalanced opener is not a clause
# bracket, so the scan ends the clause there and the word after it counts (fail closed).


@pytest.mark.parametrize(
    ("label", "word"),
    [
        ("Taxes paid, net of refunds) refund", "refund"),  # the stray ")" closes the clause
        ("Taxes paid (net of refunds [x]) and refund", "refund"),  # the nested part stays inside
        ("Taxes paid [net of refunds (x)] and receipts", "receipts"),
        ("Taxes paid net of (a (b) refunds) x", "refunds"),  # depth 2: refused, not accepted
        ("Taxes paid, net of refunds; refunded", "refunded"),  # NBSP is a space; ";" ends it
        ("Net‐of refunds. Receipts", None),  # the clause runs to the end: no word outside
        ("Tax‑refund", "refund"),  # a non-breaking hyphen separates words
        ("TAX Reimbursements", "reimbursements"),
    ],
)
def test_clause_boundaries_and_separators(label: str, word: str | None) -> None:
    found = inflow_refused(statement_issues(book((labelled(label),))))
    if word is None:
        assert found == []
    else:
        [issue] = found
        assert f'label word "{word}"' in issue


def test_a_very_long_label_is_scanned_in_linear_time() -> None:
    # 100 000 repeats of an opener inside a clause, and 200 000 plain words, must not blow up.
    nested = labelled("Taxes paid, net of " + "(refunds " * 50_000)
    assert inflow_refused(statement_issues(book((nested,)))) != []  # the unclosed "(" ends it
    plain = labelled("paid " * 200_000 + "refund")
    assert len(inflow_refused(statement_issues(book((plain,))))) == 1


def test_only_a_missing_line_withholds_an_account() -> None:
    # A not_applicable line is not "withheld as missing": the new rule is silent on it.
    base = outflow_line("CFS", "cash_taxes_paid", None)
    line = base.model_copy(
        update={"value": base.value.model_copy(update={"status": "not_applicable"})}
    )
    forged = with_accounts((line,), account("cash_taxes_paid", Decimal(15)))
    assert conflicts(statement_issues(forged)) == []


def test_each_period_of_an_account_is_checked_against_its_own_line() -> None:
    # FY2024 withheld, FY2023 known: only the FY2024 account row conflicts.
    lines = (
        outflow_line("CFS", "cash_taxes_paid", None),
        outflow_line("CFS", "cash_taxes_paid", Decimal(-9), period_id="FY2023"),
    )
    rows = (
        account("cash_taxes_paid", Decimal(15)),
        account("cash_taxes_paid", Decimal(9), "FY2023"),
    )
    [issue] = conflicts(statement_issues(with_accounts(lines, *rows)))
    assert "cash_taxes_paid FY2024 carries an amount" in issue
