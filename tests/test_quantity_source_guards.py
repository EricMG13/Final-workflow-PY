"""Counterexamples retained from Review A, with positive controls from the same sources."""

from decimal import Decimal

import pytest
import test_statement_quantities as fixtures

from deploy_vii.contracts import Citation, Span
from deploy_vii.financial_contracts import Observation, StatementLine, StatementQuantity
from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow.financial_workflow import _column_failure
from deploy_workflow.statement_compose import RowJudgment, _header_scale, compose_unit
from deploy_workflow.statement_lines import line_table

SOURCE, SHA = "filing", "a" * 64
CUE = "Amounts in millions, except per share data"
TEXT = f"""STATEMENT OF OPERATIONS
{CUE}
                              2024       2023
Net sales                       10          9
Earnings per share:
  Basic                      $ 2.42     $ 2.10
  Diluted                    $ 2.40     $ 2.08
Weighted average shares:
  Basic                         100         99
  Diluted                       101        100
"""


def compose(table, row, kind, scale, cue=CUE, locator="page:7", others=None, statement="IS"):
    return compose_unit(
        table, source_id=SOURCE, source_sha256=SHA, unit_locator=table.locator,
        kind=statement, column_periods=("FY2024", "FY2023"),
        row_map={row.line_no: RowJudgment("x", "other:x", "detail", "signed")},
        declared_periods=("FY2024", "FY2023"),
        row_label_selections={row.line_no: tuple(p.line_no for p in row.label_candidates)},
        row_dimensions={row.line_no: StatementQuantity(kind=kind, scale=scale, citations=(
            Citation(source_id=SOURCE, source_sha256=SHA, locator=locator, quote=cue),
        ))},
        typed_profile=True, book_currency="USD", book_unit="MILLIONS", context_tables=others,
    )


@pytest.mark.parametrize("value,kind,scale", [
    ("2.40", "currency_per_share", "UNITS"), ("101", "shares", "MILLIONS"),
])
def test_second_row_retains_quantity_heading(value, kind, scale):
    table = extract_statement_lines(TEXT, "page:7", SOURCE)
    row = next(r for r in table.lines if r.raw_values[0] == value)
    assert len(compose(table, row, kind, scale).lines) == 2
    assert not compose(table, row, "monetary", "MILLIONS").lines


@pytest.mark.parametrize("label,kind,scale", [
    ("Net income per ordinary share", "currency_per_share", "UNITS"),
    ("Class A common shares outstanding", "shares", "MILLIONS"),
])
def test_ordinary_and_class_share_labels(label, kind, scale):
    text = f"STATEMENT OF OPERATIONS\n{CUE}\n  2024  2023\n{label}  2.42  2.10\n"
    table = extract_statement_lines(text, "page:7", SOURCE)
    assert compose(table, table.lines[0], kind, scale).lines
    assert not compose(table, table.lines[0], "monetary", "MILLIONS").lines


def test_another_page_cannot_supply_scale():
    table = extract_statement_lines(
        "BALANCE SHEETS\n(in thousands)\n  2024  2023\nCash  1,000  900", "page:7", SOURCE
    )
    other = extract_statement_lines(
        "Note 12\n(in millions)\n  2024  2023\nGoodwill  10  10", "page:40", SOURCE
    )
    assert not compose(table, table.lines[0], "monetary", "MILLIONS", "millions",
                       "page:40", (table, other), "BS").lines


@pytest.mark.parametrize("header,correct,wrong", [
    ("(dollars in millions, shares in thousands)", "THOUSANDS", "MILLIONS"),
    ("(in thousands, except share and per share data)", "UNITS", "THOUSANDS"),
    ("(in thousands; shares not in thousands)", "UNITS", "THOUSANDS"),
])
def test_share_scale_uses_complete_header(header, correct, wrong):
    table = extract_statement_lines(
        f"STATEMENT OF OPERATIONS\n{header}\n  2024  2023\nWeighted average shares  100  99",
        "page:7", SOURCE,
    )
    assert compose(table, table.lines[0], "shares", correct, header).lines
    assert not compose(table, table.lines[0], "shares", wrong, "thousands").lines


# S11-A02: the except clause names share counts as any of its items, not only first. Expected
# scales read by hand from each header: the share item is excepted from the monetary scale, so
# the counts are in units; the monetary scale (THOUSANDS or MILLIONS) is wrong for them.
@pytest.mark.parametrize(
    "header,wrong",
    [
        ("(in thousands, except per share and share data)", "THOUSANDS"),
        ("(in millions, except per share amounts and number of shares)", "MILLIONS"),
        ("(in thousands, except per share amounts and share counts)", "THOUSANDS"),
    ],
)
def test_share_item_anywhere_in_the_except_clause_keeps_counts_in_units(header, wrong):
    table = extract_statement_lines(
        f"STATEMENT OF OPERATIONS\n{header}\n  2024  2023\n"
        "Weighted average shares  41,234,567  40,987,654",
        "page:7",
        SOURCE,
    )
    assert compose(table, table.lines[0], "shares", "UNITS", header).lines
    assert not compose(table, table.lines[0], "shares", wrong, header).lines


# A share word that is not an item of the except clause (a column heading joined after it, a new
# sentence) names no share count: the counts keep the monetary scale. Read by hand from each text.
@pytest.mark.parametrize(
    "context,scale",
    [
        ("in thousands, except per share data shares outstanding   2024   2023", "THOUSANDS"),
        ("in thousands, except per share data weighted average shares 2024 2023", "THOUSANDS"),
        ("in millions except per share data. share price information", "MILLIONS"),
        ("in thousands, except per share data, and shares outstanding", "UNITS"),
        ("in thousands, except per share data and the number of shares of common stock", "UNITS"),
        ("amounts in millions, except share amounts fiscal 2024 2023", "UNITS"),
        ("in thousands, except per share data and share counts in millions", None),
    ],
)
def test_only_a_share_item_of_the_except_clause_excepts_the_counts(context, scale):
    assert _header_scale(context, True) == scale


def test_a_per_share_item_alone_leaves_counts_in_the_monetary_scale():
    header = "(in millions, except per share amounts)"
    table = extract_statement_lines(
        f"STATEMENT OF OPERATIONS\n{header}\n  2024  2023\nWeighted average shares  100  99",
        "page:7",
        SOURCE,
    )
    assert compose(table, table.lines[0], "shares", "MILLIONS", header).lines
    assert not compose(table, table.lines[0], "shares", "UNITS", header).lines


def test_an_except_clause_that_also_scales_share_counts_is_refused():
    # "share counts in thousands" is not the "shares in thousands" form: refuse every scale
    header = "(in millions, except per share amounts and share counts in thousands)"
    table = extract_statement_lines(
        f"STATEMENT OF OPERATIONS\n{header}\n  2024  2023\nWeighted average shares  100  99",
        "page:7",
        SOURCE,
    )
    for scale in ("UNITS", "THOUSANDS", "MILLIONS"):
        assert not compose(table, table.lines[0], "shares", scale, header).lines


def test_explicit_euros_cannot_enter_a_usd_book():
    table = extract_statement_lines(
        "STATEMENT OF OPERATIONS\n(in millions of euros)\n  2024  2023\nNet sales  € 100  € 90",
        "page:7", SOURCE,
    )
    assert not compose(table, table.lines[0], "monetary", "MILLIONS", "millions").lines


def test_html_heading_applies_to_both_eps_rows():
    lines = ["STATEMENT OF OPERATIONS", CUE, "Year Ended 2024 2023", "Earnings per share:",
             "Basic $ 2.42 $ 2.10", "Diluted $ 2.40 $ 2.08"]
    table = line_table({i: Span(locator=f"line:{i}", text=t) for i, t in enumerate(lines, 1)},
                       "line:1-6", SOURCE)
    for row in table.lines:
        assert compose(table, row, "currency_per_share", "UNITS", locator="line:2").lines
        assert not compose(table, row, "monetary", "MILLIONS", locator="line:2").lines


def test_hand_written_untyped_eps_does_not_bypass_gate():
    table = extract_statement_lines(TEXT, "page:7", SOURCE)
    row = next(r for r in table.lines if r.raw_values[0] == "2.40")
    citation = Citation(source_id=SOURCE, source_sha256=SHA, locator="page:7", quote="Diluted")
    line = StatementLine(line_id="dil", statement="IS", item_id="other:dil", label="Diluted",
        period_id="FY2024", display_priority=1, line_kind="detail",
        value=Observation(observation_id="dil.FY2024", status="known", amount=Decimal("2.40"),
                          citations=(citation,)))
    result = _column_failure(fixtures.book((line,)), table, row, "IS",
                             (frozenset({"FY2024"}), Decimal("2.40")), SHA, (table,))
    assert result is not None and result[0] == 2
