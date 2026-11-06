"""S08 review regressions: header scale exceptions, per-share captions, declared currency and
outflow-magnitude totals in the statement composer. Expected outcomes are literal."""

from decimal import Decimal

import pytest

from deploy_vii.contracts import Citation
from deploy_vii.financial_contracts import StatementQuantity
from deploy_vii.statement_extract import ExtractedLine, ExtractedTable, extract_statement_lines
from deploy_workflow.statement_compose import RowJudgment, compose_unit

SOURCE, SHA = "filing", "a" * 64


def _table(header: str, row: str):
    text = f"STATEMENT OF OPERATIONS\n{header}\n  2024  2023\n{row}\n"
    return extract_statement_lines(text, "page:7", SOURCE)


def _compose(table, kind, scale, cue, *, currency="USD", unit="MILLIONS"):
    row = table.lines[0]
    return compose_unit(
        table, source_id=SOURCE, source_sha256=SHA, unit_locator=table.locator,
        kind="IS", column_periods=("FY2024", "FY2023"),
        row_map={row.line_no: RowJudgment("x", "other:x", "detail", "signed")},
        declared_periods=("FY2024", "FY2023"),
        row_label_selections={row.line_no: tuple(p.line_no for p in row.label_candidates)},
        row_dimensions={row.line_no: StatementQuantity(kind=kind, scale=scale, citations=(
            Citation(
                source_id=SOURCE, source_sha256=SHA, locator="page:7", quote=cue.split("\n")[0]
            ),
        ))},
        typed_profile=True, book_currency=currency, book_unit=unit,
    )


SHARE_ROW = "Weighted average shares outstanding  150,234,000  149,876,000"


@pytest.mark.parametrize("header", [
    "(in millions, except per share and share amounts)",
    "(in millions, except number of shares and per share amounts)",
    "(in thousands, except share counts and per share data)",
    "(In Millions, Except Per Share And Share Amounts)",
])
def test_share_count_exception_resolves_units(header):
    table = _table(header, SHARE_ROW)
    composed = _compose(table, "shares", "UNITS", header)
    assert [line.value.amount for line in composed.lines] == [
        Decimal(150234000), Decimal(149876000)
    ]
    assert all(line.quantity.scale == "UNITS" for line in composed.lines)
    assert not _compose(table, "shares", "MILLIONS", header).lines
    assert not _compose(table, "shares", "THOUSANDS", header).lines


def test_share_price_exception_does_not_unscale_share_counts():
    header = "(in millions, except share prices)"
    table = _table(header, "Weighted average shares outstanding  150.2  149.9")
    assert len(_compose(table, "shares", "MILLIONS", header).lines) == 2
    assert not _compose(table, "shares", "UNITS", header).lines


def test_a_company_name_is_not_a_currency_declaration():
    header = "STERLING INFRASTRUCTURE, INC. (in millions)"
    table = _table(header, "Net sales  100  90")
    assert len(_compose(table, "monetary", "MILLIONS", header).lines) == 2


def test_per_share_only_exception_keeps_share_counts_on_header_scale():
    header = "(in millions, except per share amounts)"
    table = _table(header, "Weighted average shares outstanding  150.2  149.9")
    assert len(_compose(table, "shares", "MILLIONS", header).lines) == 2
    assert not _compose(table, "shares", "UNITS", header).lines


@pytest.mark.parametrize("label", [
    "Earnings per diluted share",
    "Net income per-share, basic",
    "Earnings per ADS",
    "Net income per basic and diluted share",
])
def test_per_share_captions_are_currency_per_share(label):
    header = "(in millions, except per share amounts)"
    table = _table(header, f"{label}  1.23  1.05")
    composed = _compose(table, "currency_per_share", "UNITS", header)
    assert [line.value.amount for line in composed.lines] == [Decimal("1.23"), Decimal("1.05")]
    assert not _compose(table, "monetary", "MILLIONS", header).lines


def test_per_share_hyphenated_header_supports_per_share_rows():
    header = "(in millions, except per-share amounts)"
    table = _table(header, "Diluted earnings per share  1.23  1.05")
    assert len(_compose(table, "currency_per_share", "UNITS", header).lines) == 2


def test_per_unit_exception_keeps_monetary_scale_and_per_unit_rows():
    header = "(in millions, except per unit amounts)"
    money = _table(header, "Total revenues  1,234  1,100")
    composed = _compose(money, "monetary", "MILLIONS", header)
    assert [line.value.amount for line in composed.lines] == [Decimal(1234), Decimal(1100)]
    per_unit = _table(header, "Net income per limited partner unit  1.23  1.05")
    assert len(_compose(per_unit, "currency_per_share", "UNITS", header).lines) == 2
    assert not _compose(per_unit, "monetary", "MILLIONS", header).lines


@pytest.mark.parametrize("currency,header", [
    ("USD", "(in millions of swiss francs)"),
    ("USD", "(CHF in millions)"),
    ("USD", "(in millions of japanese yen)"),
    ("USD", "(JPY in millions)"),
    ("USD", "(in millions of yen)"),
    ("USD", "(in millions of australian dollars)"),
    ("USD", "(in millions of rand)"),
    ("EUR", "(in millions of dollars)"),
    ("CAD", "(in millions of dollars)"),
    ("CHF", "(in millions of euros)"),
    ("USD", "In millions of rand\nYear Ended December 31,"),
])
def test_declared_currency_other_than_book_is_refused(currency, header):
    table = _table(header, "Net sales  100  90")
    assert not _compose(table, "monetary", "MILLIONS", header, currency=currency).lines


@pytest.mark.parametrize("currency,header", [
    ("USD", "(in millions of dollars)"),
    ("USD", "(in millions of U.S. dollars)"),
    ("CHF", "(in millions of swiss francs)"),
    ("CHF", "(CHF in millions)"),
    ("JPY", "(in millions of yen)"),
    ("AUD", "(in millions of australian dollars)"),
    ("CAD", "(in millions of Canadian dollars)"),
    ("EUR", "(in millions of euros)"),
    ("USD", "(in millions)"),
    ("USD", "In millions of U.S. dollars\nYear Ended December 31,"),
    ("CHF", "In millions of Swiss francs\nYear Ended December 31,"),
])
def test_declared_book_currency_is_accepted(currency, header):
    table = _table(header, "Net sales  100  90")
    composed = _compose(table, "monetary", "MILLIONS", header, currency=currency)
    assert [line.value.amount for line in composed.lines] == [Decimal(100), Decimal(90)]


def _cfs_line(number, label, value):
    return ExtractedLine(f"line:{number}", number, label, (value,), (Decimal(value),), 0, None)


def _cfs(net):
    table = ExtractedTable("line:1", (), (
        _cfs_line(2, "Net cash provided by operating activities", "800"),
        _cfs_line(3, "Net cash used in investing activities", "500"),
        _cfs_line(4, "Net cash used in financing activities", "100"),
        _cfs_line(5, "Net increase in cash", net),
    ), source_id="s1")
    row_map = {
        2: RowJudgment("cfo", "cfo_ncfo", "total", "signed"),
        3: RowJudgment("inv", "investing_cash_flow", "total", "outflow_magnitude"),
        4: RowJudgment("fin", "financing_cash_flow", "total", "outflow_magnitude"),
        5: RowJudgment("net", "net_cash_change", "total", "signed"),
    }
    return compose_unit(table, source_id="s1", source_sha256="0" * 64, unit_locator="line:1",
                        kind="CFS", column_periods=["FY2024"], row_map=row_map,
                        declared_periods={"FY2024"})


def test_cfs_check_reads_outflow_magnitude_as_negative():
    composed = _cfs("200")
    assert composed.issues == ()
    assert composed.checks_applied == ("cfs_sections_eq_net_change",)
    assert [(line.line_id, line.value.amount) for line in composed.lines] == [
        ("cfo", Decimal(800)), ("inv", Decimal(500)), ("fin", Decimal(100)),
        ("net", Decimal(200)),
    ]


def test_cfs_check_still_fails_on_a_wrong_net_change():
    composed = _cfs("1400")
    assert composed.lines == ()
    assert [(issue.lhs, issue.rhs) for issue in composed.issues] == [
        (Decimal(200), Decimal(1400))
    ]
