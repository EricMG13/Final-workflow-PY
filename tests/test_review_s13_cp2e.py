"""Review S13: CP-2E regressions (sign, source fidelity, calendar year, published text, display
precision, citations, the reader). Expected values are literals written from the frozen
financial pages (cases/financial), not from production calculations."""

import copy
import dataclasses
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

from test_method_cp2e import SUBMISSIONS, _issues_with, _names, _pages

from deploy_vii.contracts import Module
from deploy_vii.execution import Execution, head_of
from deploy_workflow.owners import cp2e

_INTEREST = "Cash interest paid  1.25  1.25  1.25  1.25  5.00"
_INTEREST_OUT = "Cash interest paid  (1.25)  (1.25)  (1.25)  (1.25)  (5.00)"
_DEBT = "Total debt  45  46.25  47.50  48.75  50.00  50.00"
_EBITDA = "Reported EBITDA  7.5  7.5  7.5  7.5  30.0"


def _positive() -> dict[str, Any]:
    return copy.deepcopy(SUBMISSIONS["positive"])


def _swap(pages: dict[str, str], loc: str, old: str, new: str) -> dict[str, str]:
    assert old in pages[loc]
    return {**pages, loc: pages[loc].replace(old, new)}


def _row(loc: str, quote: str, value: str) -> dict[str, str]:
    return {"source_id": "financial", "locator": loc, "quote": quote, "value_text": value}


def _cell(result: cp2e.MacroFxResult, fact_id: str) -> cp2e.Cell:
    return next(c for t in result.tables for r in t.rows for c in r.cells if c.fact_id == fact_id)


def _compute(raw: dict[str, Any]) -> cp2e.MacroFxResult:
    return cp2e.compute(cp2e.inputs_from_submission(raw, source_names=_names("positive")))


# --- cash interest printed as an outflow (adversarial high, cp2e.py:782 / 233 / 502) ----------
def test_interest_in_accounting_parentheses_is_an_outflow_magnitude() -> None:
    pages = _swap(_pages("positive"), "page:3", _INTEREST, _INTEREST_OUT)
    raw = _positive()
    raw["earnings"]["interest"] = _row("page:3", _INTEREST_OUT, "(5.00)")
    assert cp2e.validate_macro_fx(submission=raw, pages=pages) == ()
    result = _compute(raw)
    s = result.sensitivity
    # EBITDA 30 over interest 5 is 6.00x; +100bp on the floating 50 adds 0.5, so 5.5 after.
    assert s.cov_base.amount == Decimal(6)
    assert s.rate[0].gross.amount == Decimal("0.5")
    assert s.rate[0].interest_after.amount == Decimal("5.5")
    assert s.rate[1].interest_after.amount == Decimal(6)  # +200bp adds 1
    assert s.rate[1].cov_after.amount == Decimal(5)
    cell = _cell(result, "T2F.1.r08.value")
    assert (cell.amount, cell.value_class) == (Decimal(5), "normalized")
    assert cell.formula == (
        "printed as an outflow in accounting parentheses; sign reversed to its magnitude"
    )
    assert _cell(result, "T2F.1.r08.basis").text == (
        "Cash flow statement, FY column, outflow in parentheses read as a positive amount"
    )


def test_interest_printed_unsigned_stays_a_source_fact() -> None:
    cell = _cell(_compute(_positive()), "T2F.1.r08.value")
    assert (cell.amount, cell.value_class, cell.formula) == (Decimal(5), "source", None)


def test_total_debt_in_parentheses_is_refused() -> None:
    printed = "Total debt  (45)  (46.25)  (47.50)  (48.75)  (50.00)  (50.00)"
    pages = _swap(_pages("positive"), "page:4", _DEBT, printed)
    raw = _positive()
    raw["earnings"]["total_debt"] = _row("page:4", printed, "(50.00)")
    assert cp2e.validate_macro_fx(submission=raw, pages=pages) == (
        "earnings.total_debt: value_text (50.00) is negative; total debt is never below zero",
    )


# --- a fixed-rate reference rate is checked against its quote (adversarial medium, :835) -------
_FIXED_BASIS = "rate_exposure.rate_basis: reference_rate does not occur in the quote"


def _fixed(quote: str, reference: str) -> tuple[str, ...]:
    raw = _positive()
    raw["rate_exposure"]["rate_basis"] = {
        "source_id": "financial",
        "locator": "page:9",
        "quote": quote,
        "rate_type": "FIXED",
        "reference_rate": reference,
    }
    pages = {**_pages("positive"), "page:9": quote}
    return cp2e.validate_macro_fx(submission=raw, pages=pages)


def test_fixed_rate_reference_rate_absent_from_its_quote_is_refused() -> None:
    issues = _fixed("The notes bear a fixed rate coupon.", "SOFR plus 450 bps, step-up 2027")
    assert issues == (_FIXED_BASIS,)


def test_fixed_rate_reference_rate_in_its_quote_is_accepted() -> None:
    assert _fixed("The notes bear a fixed rate set over the SOFR swap rate.", "SOFR swap") == ()


# --- a non-calendar fiscal year is refused (adversarial low, :402) ------------------------------
def _year_end(loc: str, statement: str) -> tuple[str, ...]:
    pages = _swap(_pages("positive"), loc, "NORTHBRIDGE SYNTHETIC GROUP", statement)
    return cp2e.validate_macro_fx(submission=_positive(), pages=pages)


def test_a_september_year_end_is_refused() -> None:
    issues = _year_end(
        "page:2", "NORTHBRIDGE SYNTHETIC GROUP, fiscal year ended September 30, 2025"
    )
    assert issues == (
        (
            "financial page:2: the statements need a calendar fiscal year (1 January to 31 "
            "December), but the page states a year end of September 30"
        ),
    )


def test_a_day_first_june_year_end_is_refused() -> None:
    issues = _year_end("page:1", "NORTHBRIDGE SYNTHETIC GROUP. For the year ended 30 June 2025.")
    assert issues == (
        (
            "financial page:1: the statements need a calendar fiscal year (1 January to 31 "
            "December), but the page states a year end of June 30"
        ),
    )


def test_a_december_year_end_is_accepted() -> None:
    assert _year_end("page:1", "NORTHBRIDGE SYNTHETIC GROUP. Fiscal year end: December 31.") == ()
    assert _year_end("page:2", "NORTHBRIDGE SYNTHETIC GROUP, year ended 31 December 2025") == ()


def test_a_quarter_end_is_not_a_year_end() -> None:
    assert _year_end("page:1", "NORTHBRIDGE SYNTHETIC GROUP. Quarter ended September 30.") == ()


# --- published analyst text carries no prohibited conclusion (code review, :871) ---------------
def test_shock_rationale_with_a_recommendation_is_refused() -> None:
    raw = _positive()
    raw["shock_rationale"] = "Rates may rise; we recommend investors sell the bonds"
    assert _issues_with(raw) == ("shock_rationale: text carries a prohibited conclusion",)


def test_absence_reason_with_a_recommendation_is_refused() -> None:
    raw = _positive()
    raw["hedge_absence"]["reason"] = "No hedge is disclosed, so sell the notes"
    assert _issues_with(raw) == ("hedge_absence.reason: text carries a prohibited conclusion",)


# --- the shown figures keep their quoted precision (code review, :1404) -------------------------
def test_hedge_ratio_is_shown_at_its_quoted_precision() -> None:
    raw = _positive()
    raw["hedge_absence"] = None
    raw["hedge_ratio"] = {"percent_text": "37.5", "rationale": "The policy hedges part of it"}
    cell = _cell(_compute(raw), "T2F.5.r01.value")
    assert (cell.amount, cell.decimals, cell.shown) == (Decimal("0.375"), 1, "37.5%")


def test_whole_hedge_ratio_keeps_whole_percent() -> None:
    raw = _positive()
    raw["hedge_absence"] = None
    raw["hedge_ratio"] = {"percent_text": "40", "rationale": "The policy hedges part of it"}
    cell = _cell(_compute(raw), "T2F.5.r01.value")
    assert (cell.amount, cell.decimals, cell.shown) == (Decimal("0.4"), 0, "40%")


def test_foreign_ebitda_share_is_shown_at_its_quoted_precision() -> None:
    raw = _positive()
    raw["fx"]["operating_fx_absence"] = None
    raw["fx"]["foreign_ebitda_share"] = {
        "source_id": "financial",
        "locator": "page:9",
        "quote": "Other currencies earn 12.25 percent of EBITDA.",
        "percent_text": "12.25",
    }
    cell = _cell(_compute(raw), "T2F.1.r12.value")
    assert (cell.amount, cell.decimals, cell.shown) == (Decimal("0.1225"), 2, "12.25%")


def test_statement_row_is_shown_at_its_quoted_precision() -> None:
    printed = "Reported EBITDA  7.5  7.5  7.5  7.5  30.125"
    pages = _swap(_pages("positive"), "page:2", _EBITDA, printed)
    raw = _positive()
    raw["earnings"]["ebitda"] = _row("page:2", printed, "30.125")
    assert cp2e.validate_macro_fx(submission=raw, pages=pages) == ()
    cell = _cell(_compute(raw), "T2F.1.r07.value")
    assert (cell.amount, cell.decimals, cell.shown) == (Decimal("30.125"), 3, "30.125")


def test_statement_row_beyond_six_places_is_refused() -> None:
    printed = "Reported EBITDA  7.5  7.5  7.5  7.5  30.0000001"
    pages = _swap(_pages("positive"), "page:2", _EBITDA, printed)
    raw = _positive()
    raw["earnings"]["ebitda"] = _row("page:2", printed, "30.0000001")
    assert cp2e.validate_macro_fx(submission=raw, pages=pages) == (
        "earnings.ebitda: value_text 30.0000001 has more than 6 decimal places",
    )


def test_two_place_rows_keep_two_places() -> None:
    cell = _cell(_compute(_positive()), "T2F.1.r07.value")
    assert (cell.amount, cell.decimals, cell.shown) == (Decimal(30), 2, "30.00")


# --- T2F.2.r06 cites the facility balance it divides (code review R2, :1325) -------------------
def test_foreign_debt_share_cites_the_facility_balance() -> None:
    inputs = cp2e.inputs_from_submission(_positive(), source_names=_names("positive"))
    assert inputs.facility is not None
    moved = cp2e.Cite("financial", "page:9", "balance of 50")
    facility = dataclasses.replace(
        inputs.facility, balance=dataclasses.replace(inputs.facility.balance, cite=moved)
    )
    result = cp2e.compute(dataclasses.replace(inputs, facility=facility))
    cites = _cell(result, "T2F.2.r06.value").cites
    assert cites == (
        ("financial", "page:9"),
        ("financial", "page:5"),
        ("financial", "page:1"),
        ("financial", "page:4"),
    )
    assert cites[0].quote == "balance of 50"


# --- the reader reports an unsettled head (code review, :2161) ----------------------------------
def test_reader_reports_a_blocked_head_without_figures() -> None:
    module = Module(
        run_id="run-1",
        issuer_id="issuer-1",
        as_of=date(2026, 1, 10),
        module_id="CP-2E",
        status="blocked",
        limitations=("The macro_fx step was refused",),
    )
    head = head_of(module)
    store = SimpleNamespace(head_module=lambda h: module)
    read = cp2e.cp2e_reader(cast(Execution, store), head)
    assert (read.status, read.head_sha256) == ("blocked", head.result_sha256)
    assert (read.floating_debt, read.foreign_debt, read.hedge_ratio, read.shocks) == (
        None,
        None,
        None,
        (),
    )
    assert read.limitations == ("The macro_fx step was refused",)
