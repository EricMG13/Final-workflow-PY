"""Second-model review of the S11/S12/S13 low fixes: adversarial cases, expected values by hand."""

import json
import sys
from datetime import date
from decimal import Decimal as D

import openpyxl
import test_financial_workflow as workflow_fixture
import test_portfolio_input_guards as pg
import test_statement_quantity_outputs as quantity_fixtures
from test_addback_exclusion import _addback, _registers
from test_cash_scope import book, cite, line, period
from test_financial_series import change, fixture

import deploy_vii.financial_adapter as adapter
from deploy_vii import statement_validation as sv
from deploy_vii.canonical_audit import DefinitionReview
from deploy_vii.canonical_gaps import canonical_gaps
from deploy_vii.canonical_tables import COLUMNS, _keys, _projection_gap_rows, _row
from deploy_vii.context_binding import FinancialContextBinding
from deploy_vii.contracts import Span
from deploy_vii.financial_contracts import FinancialReview, Observation
from deploy_vii.financial_periods import historical_report
from deploy_vii.model.statements import excluded_addbacks
from deploy_vii.model_interface import _Tables
from deploy_vii.period_reconciliation import reconcile_periods
from deploy_vii.prose import bare_figures, run_name
from deploy_vii.source_context import SourceContextReview
from deploy_workflow import financial_workflow as fw
from deploy_workflow.financial_series import cp1_chart_series
from deploy_workflow.pdf_headers import mapping_headers


def _two_books():
    stmt_items = {m: k for k, m in sv.ACCOUNT_LINKS.items()}
    revenue = stmt_items["revenue"]
    periods = (period("p1", "FY", None, "FY2024", date(2024, 1, 1), date(2024, 12, 31)),)
    first = book().model_copy(
        update={
            "periods": periods,
            "accounts": (),
            "statement_lines": (line("l1", *revenue, "p1", 100, cite("revenue 100")),),
        }
    )
    second = first.model_copy(
        update={"statement_lines": (line("l1", *revenue, "p1", 7, cite("revenue 7")),)}
    )
    return first, second


def _revenue(index: sv._AccountIndex) -> list[D | None]:
    return [r.value.amount for r in index.by_metric.get("revenue", ())]


def test_alternating_books_each_get_their_own_accounts() -> None:
    # By hand: book one states revenue 100, book two (equal shape, another object) 7; asking in
    # the order one, two, one gives 100, 7, 100: the kept index never answers for another book.
    first, second = _two_books()
    sv._last_index = None
    amounts = [_revenue(sv._account_index(b)) for b in (first, second, first)]
    assert amounts == [[D(100)], [D(7)], [D(100)]]


def test_a_writer_between_any_two_steps_never_hands_over_another_books_index() -> None:
    # By hand: the index of book one is kept; while book one's lookup runs, another thread stores
    # book two's index. Wherever that store lands between two bytecode steps, book one's lookup
    # must answer 100 (its own index, kept or rebuilt), never book two's 7.
    first, second = _two_books()
    sv._last_index = None
    other = (second, sv._account_index(second))
    code = sv._account_index.__code__
    results = []
    for step in range(200):
        sv._last_index = None
        sv._account_index(first)  # book one's index is the kept one
        seen = 0

        def tracer(frame, event, arg, step=step):
            nonlocal seen
            if frame.f_code is not code:
                return None
            frame.f_trace_opcodes = True
            if event == "opcode":
                if seen == step:
                    sv._last_index = other
                seen += 1
            return tracer

        sys.settrace(tracer)
        try:
            index = sv._account_index(first)
        finally:
            sys.settrace(None)
        results.append(_revenue(index))
        if seen <= step:
            break
    assert results and all(r == [D(100)] for r in results)


# --- S13-A08/A09: portfolio guards --------------------------------------------------------------


def test_a_hidden_column_is_one_issue_per_row_at_the_hidden_cell() -> None:
    # By hand: Top_Holdings has a header and two holdings; column C (instrument) is hidden, so the
    # filled cells C1, C2 and C3 are hidden: one issue for each of rows 1, 2 and 3.
    def hide(book: openpyxl.Workbook) -> None:
        book["Top_Holdings"].column_dimensions["C"].hidden = True

    issues = pg.validate_portfolio_bytes("p.xlsx", pg._workbook(pg.valid(), hide)).issues
    assert [(i.cell, i.problem) for i in issues] == [
        ("C1", "row 1 holds hidden cells"),
        ("C2", "row 2 holds hidden cells"),
        ("C3", "row 3 holds hidden cells"),
    ]


def test_a_hidden_empty_row_is_no_issue() -> None:
    # By hand: row 9 of Maturity_Profile is hidden but holds nothing; nothing hidden is read.
    def hide(book: openpyxl.Workbook) -> None:
        book["Maturity_Profile"].row_dimensions[9].hidden = True

    assert pg._problems(pg.valid(), hide) == []


def test_a_negative_headroom_of_a_breached_sector_is_not_a_negative_share() -> None:
    # By hand: Insurance is 5 % NAV against a 4 % limit, headroom 4 - 5 = -1, a Breach. Only
    # pct_nav must be at least 0; a negative headroom is the breach itself.
    data = pg.valid()
    data["Sector_Exposure"][1] |= {
        "limit_pct_nav": "4",
        "headroom_pct_nav": "-1",
        "status": "Breach",
    }
    assert pg._problems(data) == []


def test_a_negative_percent_formatted_share_is_one_issue() -> None:
    # By hand: -0.0237 shown as -2.37 % is refused once, as negative; the dropped value is not
    # also reported as percent-formatted.
    data = pg.valid()
    data["Top_Holdings"][0]["pct_nav"] = -0.0237

    def percent(book: openpyxl.Workbook) -> None:
        book["Top_Holdings"]["D2"].number_format = "0.00%"

    assert pg._problems(data, percent) == ["pct_nav '-0.0237' is negative"]


def test_a_percent_formatted_value_on_a_count_row_is_not_a_share() -> None:
    # By hand: obligors is a count (unit "count"), not % NAV; its format scales nothing read.
    def percent(book: openpyxl.Workbook) -> None:
        book["Exposure_Summary"]["B3"].number_format = "0%"

    assert pg._problems(pg.valid(), percent) == []


# --- S13-C08: an issuer name in claim text ------------------------------------------------------


def test_reserved_characters_of_a_name_read_as_round_brackets() -> None:
    # By hand: each of [ ] { } becomes ( or ); nothing else changes.
    assert run_name("{Acme} [UK] Ltd") == "(Acme) (UK) Ltd"
    assert run_name("Acme (UK) Ltd") == "Acme (UK) Ltd"


def test_the_mapped_name_covers_only_its_own_digits() -> None:
    # By hand: "Fund [2] LP" reads "Fund (2) LP" in run text; its 2 is the name, the 3 and the 5
    # are figures.
    names = ("Fund [2] LP",)
    assert bare_figures("Fund (2) LP reported", names=names) == ()
    assert bare_figures("Fund (2) LP grew 5", names=names) == ("5",)
    assert bare_figures("Fund (3) LP", names=names) == ("3",)


# --- S13-C09: the projection-gap rows keep T4.11 and T4.13 gaps ---------------------------------


def test_definition_and_readiness_blanks_are_still_registered() -> None:
    # By hand: a T4.11 row with no periods (field_4 empty) and a T4.13 row with no gaps (field_2
    # empty) are two ledger gaps; each gets its T4.12 WARN row, naming its own field.
    tables = _Tables(
        quantity_fixtures._book(),
        schemas={k: (title, None, _keys(k)) for k, (title, _) in COLUMNS.items()},
    )
    _row(
        tables, "T4.11", "d1", "Unspecified period", ("m", "c", "i", "s", None, "x", "y", "z", "w")
    )
    _row(tables, "T4.13", "CP-2", "Consumer-specific scope", ("CP-2", "READY", None, "none"))
    assert [(g.table_id, g.field) for g in tables.gaps] == [
        ("T4.11", "field_4"),
        ("T4.13", "field_2"),
    ]
    _projection_gap_rows(tables)
    rows = {f.row_id: {} for f in tables.facts if f.table_id == "T4.12"}
    for fact in tables.facts:
        if fact.table_id == "T4.12":
            rows[fact.row_id][fact.field] = fact.text
    assert [(r["field_0"].split("/")[0], r["field_1"], r["field_4"]) for r in rows.values()] == [
        ("T4.11", "field_4", "WARN"),
        ("T4.13", "field_2", "WARN"),
    ]


# --- S12-C02: a CP-1 row with no figure still states its realisation -----------------------------


def test_a_not_stated_cp1_row_without_a_figure_still_excludes() -> None:
    # By hand: CP-1 gives "ns" a NOT_STATED row whose figure is missing (null amount, a reason);
    # the row is CP-1's own, so the house variant leaves "ns" out; missing is not zero.
    missing = Observation(
        observation_id="ab-ns", status="missing", amount=None, citations=(), reason="not given"
    )
    row = _addback("ns", "NOT_STATED", 0).model_copy(update={"value": missing})
    regs = _registers(row)
    own = [r for r in regs.addbacks if r.source is not None]
    assert [(r.period_id, r.value) for r in own] == [("fy-2025", None)]
    assert excluded_addbacks(regs, True) == {"ns"}


# --- S11-C08: a register that mixes scopes ------------------------------------------------------


def test_one_period_in_another_currency_gives_every_figure_the_reason() -> None:
    # By hand: one T4.14 period states EUR, the rest USD; nothing is converted, so S.1 to S.5
    # plot no point and carry the one reason.
    module = fixture()
    first = next(f.row_id for f in module.facts if f.table_id == "T4.14")
    figures = cp1_chart_series(
        change(module, table="T4.14", field="currency", row=first, text="EUR")
    )
    assert [f.fig_id for f in figures] == ["S.1", "S.2", "S.3", "S.4", "S.5"]
    assert {f.points for f in figures} == {()}
    assert len({f.reason for f in figures}) == 1


# --- S11-C07: ordinals and month-year banners ---------------------------------------------------


def test_an_ordinal_day_still_maps_and_a_month_year_banner_does_not() -> None:
    # By hand: "June 30th" over 2024 2023 is June 30 of each year; "Year ended June 2024" names no
    # day, so the 20 of 2024 is not read as June 20 and the header maps to nothing.
    ordinal = "Balance sheet\nAs at June 30th\n2024  2023\nAssets\nCash 1 2\n"
    assert mapping_headers(ordinal, first_data_line=5, statement="BS") == (
        "June 30, 2024 | June 30, 2023",
    )
    banner = "Statement of operations\nYear ended June 2024\n2024  2023\nRevenue 1 2\n"
    assert mapping_headers(banner, first_data_line=4, statement="IS") is None


# --- S11-C09: page units are cached by content --------------------------------------------------


def test_page_units_follow_the_page_text_not_the_locator() -> None:
    # By hand: the same locator page:1 holds a balance sheet, then an income statement; each read
    # gives its own kind, also after ten other sources have pushed the first out of the cache.
    bs = (Span(locator="page:1", text="CONSOLIDATED BALANCE SHEETS\n2025  2024\nCash  10  9"),)
    is_ = (
        Span(
            locator="page:1",
            text="CONSOLIDATED STATEMENTS OF OPERATIONS\n2025  2024\nRevenue  10  9",
        ),
    )
    assert fw._page_units(bs) == {"page:1": "BS"}
    assert fw._page_units(is_) == {"page:1": "IS"}
    for n in range(10):
        fw._page_units((Span(locator="page:1", text=f"BALANCE SHEET\n2025  2024\nCash  {n}  9"),))
    assert fw._page_units(bs) == {"page:1": "BS"}


# --- S12-C07/S13-C11: one gap build validates once and reconciles the KPI history ----------------


def test_canonical_gaps_validates_once_and_its_reconciliation_is_the_independent_one(
    monkeypatch,
) -> None:
    # Synthetic test_financial_workflow fixture (one USD/IFRS book). By hand: the gap build needs
    # the registers once; before the change it validated the review four times. Its KPI history
    # and period reconciliation equal the ones built from the pack and review alone.
    pack = workflow_fixture.make_pack()
    context = SourceContextReview.model_validate_json(workflow_fixture.context(pack))
    docs = workflow_fixture.financials(pack)
    scope = {
        "currency": "USD",
        "unit": "MILLIONS",
        "accounting_basis": "IFRS",
        "entity_perimeter": "consolidated group",
    }
    docs["financial"].pop("limitations", None)
    for b in docs["financial"]["books"]:
        b.update(scope)
        for p in b["periods"]:
            p.update(scope)
    financial = FinancialReview.model_validate_json(
        json.dumps({**docs["financial"], "pack_sha256": pack.content_hash()})
    )
    definition = DefinitionReview.model_validate_json(
        json.dumps({**docs["definition"], "financial_review_sha256": financial.content_hash()})
    )
    binding = FinancialContextBinding.model_validate_json(
        json.dumps(
            {
                **docs["binding"],
                "financial_review_sha256": financial.content_hash(),
                "source_context_review_sha256": context.content_hash(),
            }
        )
    )
    calls: list[int] = []
    real = adapter.validate_financial_review
    monkeypatch.setattr(
        adapter, "validate_financial_review", lambda *a: calls.append(1) or real(*a)
    )
    report = canonical_gaps(pack, context, financial, definition, binding)
    assert len(calls) == 1
    monkeypatch.setattr(adapter, "validate_financial_review", real)
    book_id = definition.book_id
    assert report.kpis is not None
    assert report.kpis.historical == historical_report(pack, financial, book_id)
    assert report.period_reconciliation == reconcile_periods(pack, financial, book_id)
