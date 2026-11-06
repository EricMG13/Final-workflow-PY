"""Review S02 (input workbooks): percent-formatted numbers, TRUE/FALSE and error cells, bounded
exponents and the damaged/sheetless refusals. Expected texts are written out literally from the
template convention (docs/templates/README.md: a percent cell is a plain number in percent and
a percentage-formatted number is refused, never rescaled)."""

import io
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

import pytest
from openpyxl import Workbook, load_workbook

from deploy_vii.inputs.portfolio import validate_portfolio_bytes
from deploy_vii.inputs.rv_quotes import COLUMNS, validate_rv_bytes

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs" / "templates" / "portfolio.template.xlsx"
RV = "q.xlsx"
PF = "p.xlsx"
GENERAL = "General"
BASE = [
    "Dealer A",
    "2026-05-29",
    "Issuer X",
    "TLB-2030",
    "Term Loan B due 2030",
    "observed",
    99.5,
    None,
    None,
    None,
    None,
    "USD",
    None,
]


def quotes(row: list[object], formats: dict[str, str] | None = None) -> bytes:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "rv_quotes"
    sheet.append(list(COLUMNS))
    sheet.append(row)
    for cell, code in (formats or {}).items():
        sheet[cell].number_format = code
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


def lines(raw: bytes) -> list[str]:
    return list(validate_rv_bytes(RV, raw).lines())


def with_row(column: int, value: object) -> list[object]:
    row = list(BASE)
    row[column] = value
    return row


def test_a_percent_formatted_yield_is_refused_not_read_as_a_fraction() -> None:
    raw = quotes(with_row(7, 0.0725), {"H2": "0.00%"})
    assert lines(raw) == [
        (
            "q.xlsx:rv_quotes!H2: yield_pct '0.0725' is formatted as a percentage — fix: format the "
            "cell as General and enter the level as shown, e.g. 7.25 for 7.25 %"
        ),
        "FAILED: 1 issues",
    ]


def test_a_literal_percent_sign_format_is_accepted() -> None:
    assert lines(quotes(with_row(7, 7.25), {"H2": '0.00"%"'})) == ["OK: 1 rows"]


def test_a_true_false_level_and_an_error_provider_are_refused() -> None:
    assert lines(quotes(with_row(6, True))) == [
        (
            "q.xlsx:rv_quotes!G2: price holds a TRUE/FALSE cell — fix: enter text or a plain "
            "number, not TRUE or FALSE"
        ),
        "FAILED: 1 issues",
    ]
    assert lines(quotes(with_row(0, "#N/A"))) == [
        (
            "q.xlsx:rv_quotes!A2: provider holds the Excel error '#N/A' — fix: enter the real value "
            "in place of the error, or leave an optional cell empty"
        ),
        "FAILED: 1 issues",
    ]


@pytest.mark.parametrize("level", ["1e999999999999999999999", "1e-999", "1e100"])
def test_an_unbounded_exponent_is_not_a_number(level: str) -> None:
    row = with_row(6, None)
    row[9], row[10] = level, "99"
    assert lines(quotes(row)) == [
        (
            f"q.xlsx:rv_quotes!J2: bid '{level}' is not a number — fix: enter a plain number: digits, "
            "an optional sign and one decimal point (no %, units, spaces or thousands separators)"
        ),
        "FAILED: 1 issues",
    ]


def test_a_two_digit_exponent_compares_exactly() -> None:
    row = with_row(6, None)
    row[9], row[10] = "1e2", "99"
    assert lines(quotes(row)) == [
        (
            "q.xlsx:rv_quotes!J2:K2: bid 1e2 exceeds ask 99 — fix: check the quote: bid must not "
            "exceed ask"
        ),
        "FAILED: 1 issues",
    ]


def test_a_level_longer_than_forty_characters_is_refused() -> None:
    level = "1." + "0" * 39
    assert lines(quotes(with_row(6, level))) == [
        (
            f"q.xlsx:rv_quotes!G2: price '{level}' is longer than 40 characters — fix: enter the "
            "number with at most 40 characters (Excel keeps 15 significant digits)"
        ),
        "FAILED: 1 issues",
    ]


def one_member(payload: bytes, *, encrypted: bool) -> bytes:
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_STORED) as archive:
        archive.writestr("xl/workbook.xml", payload)
    raw = bytearray(stream.getvalue())
    central = raw.index(b"PK\x01\x02")
    if encrypted:
        raw[6] |= 1
        raw[central + 8] |= 1
    return bytes(raw)


def test_a_damaged_member_is_one_issue_with_the_damaged_fix() -> None:
    assert lines(one_member(b"<workbook/>", encrypted=True)) == [
        (
            "q.xlsx:rv_quotes!A1: prepare cannot read this file as an OOXML workbook: damaged ZIP "
            "member (RuntimeError: File 'xl/workbook.xml' is encrypted, password required for "
            "extraction) — fix: save the file again as an Excel Workbook (.xlsx) and validate "
            "again; prepare would also refuse this file"
        ),
        "FAILED: 1 issues",
    ]


def sheetless() -> bytes:
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("xl/workbook.xml", f'<workbook xmlns="{main}"><sheets/></workbook>')
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
        )
    return stream.getvalue()


def test_a_workbook_without_sheets_names_the_missing_sheet() -> None:
    assert lines(sheetless()) == [
        (
            "q.xlsx:rv_quotes!A1: no sheet named rv_quotes (found: none) — fix: name the quote "
            "sheet rv_quotes"
        ),
        "FAILED: 1 issues",
    ]


def test_an_empty_quote_sheet_names_the_header_row_not_a_missing_template() -> None:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "rv_quotes"
    stream = io.BytesIO()
    book.save(stream)
    assert lines(stream.getvalue()) == [
        (
            "q.xlsx:rv_quotes!A1: sheet rv_quotes is empty — fix: enter the header row (provider, "
            "as_of, issuer, facility_id, instrument, quote_kind, price, yield_pct, spread_bps, bid, "
            "ask, currency, note) in row 1 and add one row per quote"
        ),
        "FAILED: 1 issues",
    ]


def portfolio_with_exposure(value: object, unit: str, code: str) -> bytes:
    book = load_workbook(TEMPLATE)
    sheet = book["Exposure_Summary"]
    row = sheet.max_row + 1
    sheet.cell(row, 1, "cash_buffer")
    sheet.cell(row, 2, value).number_format = code
    sheet.cell(row, 3, unit)
    sheet.cell(row, 4, "2026-05-29").number_format = "@"
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


def exposure_row() -> int:
    return load_workbook(TEMPLATE)["Exposure_Summary"].max_row + 1


@pytest.mark.parametrize("unit", ["% NAV", "%"])
def test_a_percent_formatted_exposure_value_on_a_percent_row_is_refused(unit: str) -> None:
    report = validate_portfolio_bytes(PF, portfolio_with_exposure(0.031, unit, "0.0%"))
    assert [issue.render() for issue in report.issues] == [
        (
            f"p.xlsx:Exposure_Summary!B{exposure_row()}: value '0.031' is formatted as a percentage "
            "— fix: format the cell as General and enter 2.5 for 2.5 % NAV"
        )
    ]


def test_a_plain_percent_exposure_and_a_percent_formatted_amount_row_are_accepted() -> None:
    assert validate_portfolio_bytes(PF, portfolio_with_exposure(3.1, "% NAV", GENERAL)).ok
    assert validate_portfolio_bytes(PF, portfolio_with_exposure(0.5, "years", "0%")).ok


def test_a_damaged_portfolio_member_keeps_its_damaged_fix() -> None:
    report = validate_portfolio_bytes(PF, one_member(b"<workbook/>", encrypted=True))
    assert [issue.render() for issue in report.issues] == [
        (
            "p.xlsx:Mandate!A1: prepare cannot read this file as an OOXML workbook: damaged ZIP "
            "member (RuntimeError: File 'xl/workbook.xml' is encrypted, password required for "
            "extraction) — fix: save the file again as an Excel Workbook (.xlsx) and validate "
            "again; prepare would also refuse this file"
        )
    ]
