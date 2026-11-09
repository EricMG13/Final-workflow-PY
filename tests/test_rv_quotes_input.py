"""S08-cp3-A10, A11, A12: the `rv_quotes` self-check (`deploy-vii validate-input rv`).

Real XLSX bytes through `validate_rv_bytes`. Expected issue texts are written out by hand from
the rules each test names, never read back from the validator's own tables.
"""

import io
from pathlib import Path

import openpyxl
import pytest

from deploy_vii.inputs import rv_quotes
from deploy_vii.inputs.rv_quotes import COLUMNS, FIX, validate_rv_bytes

ROOT = Path(__file__).resolve().parents[1]


def _book(rows: list[dict[str, str]]) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "rv_quotes"
    sheet.append(list(COLUMNS))
    for row in rows:
        sheet.append([row.get(column) or None for column in COLUMNS])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _row(**values: str) -> dict[str, str]:
    row = {
        "provider": "Dealer A",
        "as_of": "2026-01-09",
        "issuer": "Acme",
        "facility_id": "TLB-2030",
        "instrument": "Term Loan B due 2030",
        "quote_kind": "observed",
        "currency": "USD",
    }
    row.update(values)
    return row


def _lines(rows: list[dict[str, str]]) -> tuple[str, ...]:
    return validate_rv_bytes("q.xlsx", _book(rows)).lines()


# --- A10: an exponent Decimal cannot read is "not a number", never a crash ------------------------


@pytest.mark.parametrize("lexeme", ["1e9999999999999999999999", "1e999999", "1E100", "5e-100"])
def test_a10_an_exponent_of_three_or_more_digits_is_not_a_number(lexeme: str) -> None:
    """Bid holds the lexeme, ask 1: column J (bid) of row 2 is refused as not a number, and the
    bid/ask comparison is skipped for a flagged bid."""
    assert _lines([_row(bid=lexeme, ask="1")]) == (
        f"q.xlsx:rv_quotes!J2: bid '{lexeme}' is not a number — fix: {FIX['number']}",
        "FAILED: 1 issues",
    )


def test_a10_a_two_digit_exponent_still_reads() -> None:
    """1e2 = 100 > 99.5: the comparison runs on the decimal values, so bid exceeds ask."""
    assert _lines([_row(bid="1e2", ask="99.5")]) == (
        f"q.xlsx:rv_quotes!J2:K2: bid 1e2 exceeds ask 99.5 — fix: {FIX['bid_ask']}",
        "FAILED: 1 issues",
    )


# --- A11: price above zero; duplicate key folded --------------------------------------------------


@pytest.mark.parametrize("price", ["0", "-5", "-0", "0.000", "0e5"])
def test_a11_a_price_at_or_below_zero_is_refused(price: str) -> None:
    """Column G (price) of row 2: every lexeme here is a number at or below zero."""
    assert _lines([_row(price=price)]) == (
        f"q.xlsx:rv_quotes!G2: price '{price}' is not above zero — fix: {FIX['price']}",
        "FAILED: 1 issues",
    )


def test_a11_a_positive_price_and_signed_spread_or_yield_pass() -> None:
    """Only price must be above zero; a negative yield or spread is a level (one row each)."""
    rows = [
        _row(price="98.5"),
        _row(yield_pct="-0.25", provider="Dealer B"),
        _row(spread_bps="-10", provider="Dealer C"),
    ]
    assert _lines(rows) == ("OK: 3 rows",)


@pytest.mark.parametrize(
    ("provider", "facility_id"),
    [("dealer a", "TLB-2030"), ("Dealer A", "tlb-2030"), ("DEALER   A", "Tlb-2030")],
)
def test_a11_a_key_differing_only_in_case_or_spaces_is_a_duplicate(
    provider: str, facility_id: str
) -> None:
    """Row 3 repeats row 2's facility, date, provider and kind up to case and inner spaces."""
    rows = [_row(price="98.5"), _row(price="97", provider=provider, facility_id=facility_id)]
    problem = "duplicates row 2 on facility_id, as_of, provider and quote_kind"
    assert _lines(rows) == (
        f"q.xlsx:rv_quotes!A3:F3: {problem} — fix: {FIX['duplicate']}",
        "FAILED: 1 issues",
    )


def test_a11_a_different_kind_or_date_is_not_a_duplicate() -> None:
    rows = [
        _row(price="98.5"),
        _row(price="99", provider="dealer a", quote_kind="indicative_talk"),
        _row(price="97", provider="dealer a", as_of="2026-01-10"),
    ]
    assert _lines(rows) == ("OK: 3 rows",)


# --- A12: no fix text names a file the repository does not hold -----------------------------------


def test_a12_fix_texts_name_no_missing_template() -> None:
    """The removed `TEMPLATE` named docs/templates/rv-quotes.template.xlsx, which no commit
    holds; the empty-sheet and sheet-name fixes now spell the header row and sheet name."""
    assert not hasattr(rv_quotes, "TEMPLATE")
    header = (
        "provider, as_of, issuer, facility_id, instrument, quote_kind, price, yield_pct, "
        "spread_bps, bid, ask, currency, note (A1 to M1, nothing after M1)"
    )
    assert FIX["header"] == f"set row 1 to exactly: {header}"
    assert FIX["empty"] == f"set row 1 to exactly: {header}, then add one row per quote from row 2"
    assert FIX["sheet"] == "name the quote sheet rv_quotes"
    for text in FIX.values():
        for word in text.split():
            if word.startswith("docs/"):
                assert (ROOT / word.rstrip(",.")).exists(), word


def test_a12_an_empty_sheet_gets_the_spelled_header_fix() -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "rv_quotes"
    buffer = io.BytesIO()
    workbook.save(buffer)
    assert validate_rv_bytes("q.xlsx", buffer.getvalue()).lines() == (
        f"q.xlsx:rv_quotes!A1: sheet rv_quotes is empty — fix: {FIX['empty']}",
        "FAILED: 1 issues",
    )


# --- review: boundaries the fix must keep and the duplicate fold's white space --------------------


@pytest.mark.parametrize("price", ["99.5", "101.25", "+5", ".5", "1e99", "1e-99", "5E2"])
def test_review_legitimate_prices_still_pass(price: str) -> None:
    """Every lexeme is a number above zero with at most a two-digit exponent."""
    assert _lines([_row(price=price)]) == ("OK: 1 rows",)


def test_review_a_three_digit_exponent_price_is_not_a_number_and_does_not_crash() -> None:
    assert _lines([_row(price="1e100")]) == (
        f"q.xlsx:rv_quotes!G2: price '1e100' is not a number — fix: {FIX['number']}",
        "FAILED: 1 issues",
    )


def test_review_two_digit_exponents_compare_as_values() -> None:
    """1e99 is far above 1e-99, so a bid of 1e99 exceeds an ask of 1e-99."""
    assert _lines([_row(bid="1e99", ask="1e-99")]) == (
        f"q.xlsx:rv_quotes!J2:K2: bid 1e99 exceeds ask 1e-99 — fix: {FIX['bid_ask']}",
        "FAILED: 1 issues",
    )


def test_review_a_no_break_space_provider_is_a_duplicate() -> None:
    rows = [_row(price="98.5"), _row(price="97", provider="Dealer A")]
    problem = "duplicates row 2 on facility_id, as_of, provider and quote_kind"
    assert _lines(rows) == (
        f"q.xlsx:rv_quotes!A3:F3: {problem} — fix: {FIX['duplicate']}",
        "FAILED: 1 issues",
    )
