"""S13-A08/A09: percent-formatted % NAV values, negative shares and hidden cells are refused.

The valid workbook is a copy of `valid()` of tests/product/test_inputs_portfolio.py (a small
synthetic fund), kept here because that module cannot be imported where
`scripts.build_templates` is absent. Expected issues are hand-derived from the edited cell.
"""

import io
from collections.abc import Callable
from typing import Any

import openpyxl
import pytest

from deploy_vii.inputs.portfolio import MEDIA_TYPE, portfolio_facts, validate_portfolio_bytes
from deploy_vii.preparation import SourceRequest, prepare_source

# The brief's sheets and columns, in order (stated independently of the module's constants).
SHEETS: dict[str, tuple[str, ...]] = {
    "Mandate": ("section", "field", "value", "notes"),
    "Exposure_Summary": ("metric", "value", "unit", "as_of"),
    "Rating_Distribution": ("rating_bucket", "pct_nav", "issuers"),
    "Sector_Exposure": (
        "sector",
        "pct_nav",
        "issuers",
        "limit_pct_nav",
        "headroom_pct_nav",
        "status",
    ),
    "Top_Holdings": ("rank", "issuer", "instrument", "pct_nav", "rating"),
    "Maturity_Profile": ("bucket", "pct_nav"),
    "Compliance_Monitor": (
        "id",
        "constraint_category",
        "parameter",
        "limit",
        "limit_unit",
        "breach_type",
        "scope",
        "source_document",
        "current_value",
        "headroom",
        "status",
        "last_checked",
        "checked_by",
    ),
}
AS_OF = "2026-05-29"


def _mandate(section: str, field: str, value: object, notes: object = None) -> dict[str, Any]:
    return {"section": section, "field": field, "value": value, "notes": notes}


def _control(**values: object) -> dict[str, Any]:
    row = {
        "id": "C-01",
        "constraint_category": "Single Name",
        "parameter": "Max single issuer exposure",
        "limit": "2.5",
        "limit_unit": "% NAV",
        "breach_type": "Hard",
        "scope": "issuer",
        "source_document": "Indenture s7.11 (synthetic)",
        "current_value": "2.37",
        "headroom": "0.13",
        "status": "Watch",
        "last_checked": AS_OF,
        "checked_by": "analyst",
    }
    return row | values


def valid() -> dict[str, list[dict[str, Any]]]:
    """A small valid synthetic portfolio; Exposure_Summary nav is row 2."""
    return {
        "Mandate": [
            _mandate("Strategy", "fund_name", "Example Fund I (synthetic)"),
            _mandate("Strategy", "strategy", "CLO", "synthetic"),
            _mandate("Capital Structure", "nav", 1000),
            _mandate("Capital Structure", "nav_currency", "USD"),
            _mandate("Reporting", "as_of", AS_OF),
            _mandate("Key Parties", "trustee", "Synthetic Trustee Bank"),
        ],
        "Exposure_Summary": [
            {"metric": "nav", "value": "1000.00", "unit": "USD", "as_of": AS_OF},
            {"metric": "obligors", "value": 12, "unit": "count", "as_of": AS_OF},
        ],
        "Rating_Distribution": [
            {"rating_bucket": "B", "pct_nav": "60.5", "issuers": 8},
            {"rating_bucket": "BB", "pct_nav": 39.5, "issuers": "4"},
        ],
        "Sector_Exposure": [
            {
                "sector": "Software",
                "pct_nav": "7.16",
                "issuers": 5,
                "limit_pct_nav": "10.0",
                "headroom_pct_nav": "2.84",
                "status": "Pass",
            },
            {"sector": "Insurance", "pct_nav": "5", "issuers": 2},
        ],
        "Top_Holdings": [
            {
                "rank": 1,
                "issuer": "Alpha Example Holdings (synthetic)",
                "instrument": "Term Loan B due 2030",
                "pct_nav": "2.37",
                "rating": "B3 / B",
            },
            {
                "rank": "2",
                "issuer": "Beta Sample Industries (synthetic)",
                "instrument": "Senior Secured Notes due 2032",
                "pct_nav": "1.91",
                "rating": "Ba3 / BB-",
            },
        ],
        "Maturity_Profile": [
            {"bucket": "3-5 Years", "pct_nav": "40"},
            {"bucket": "5-7 Years", "pct_nav": "60"},
        ],
        "Compliance_Monitor": [
            _control(),
            _control(
                id="SECTOR",
                constraint_category="Sector",
                parameter="Max single sector",
                limit="10.0",
                breach_type="Soft",
                scope="sector",
                current_value="4.57",
                headroom="5.43",
                status="Pass",
            ),
        ],
    }


Tweak = Callable[[openpyxl.Workbook], None]


def _workbook(data: dict[str, list[dict[str, Any]]], tweak: Tweak | None = None) -> bytes:
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name, columns in SHEETS.items():
        if name in data:
            sheet = book.create_sheet(name)
            sheet.append(list(columns))
            for row in data[name]:
                sheet.append([row.get(column) for column in columns])
    if tweak is not None:
        tweak(book)
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


def _problems(data: dict[str, list[dict[str, Any]]], tweak: Tweak | None = None) -> list[str]:
    return [
        issue.problem for issue in validate_portfolio_bytes("p.xlsx", _workbook(data, tweak)).issues
    ]


def test_the_untouched_workbook_is_accepted() -> None:
    assert _problems(valid()) == []


def test_a_percent_formatted_nav_share_on_a_percent_nav_exposure_row_is_refused() -> None:
    # By hand: cash is 2.5 % NAV, shown 2.50 % in Excel and stored 0.025; read as a plain number it
    # would be 0.025 % NAV, 100 times too small, so the cell is refused instead.
    data = valid()
    data["Exposure_Summary"].append(
        {"metric": "cash", "value": 0.025, "unit": "% NAV", "as_of": "2026-05-29"}
    )
    cash_row = len(data["Exposure_Summary"]) + 1

    def percent(book: openpyxl.Workbook) -> None:
        book["Exposure_Summary"][f"B{cash_row}"].number_format = "0.00%"

    assert _problems(data, percent) == ["value '0.025' is formatted as a percentage"]
    data["Exposure_Summary"][-1]["value"] = "2.5"
    assert _problems(data) == []  # the plain 2.5 is accepted
    data["Exposure_Summary"][-1]["unit"] = "USD"
    assert _problems(data, percent) == []  # a currency amount may be percent-formatted text only


@pytest.mark.parametrize(
    "sheet,index",
    [("Maturity_Profile", 0), ("Top_Holdings", 0), ("Sector_Exposure", 0)],
)
def test_a_negative_pct_nav_is_refused(sheet: str, index: int) -> None:
    # By hand: -40 % NAV is not a share of NAV.
    data = valid()
    data[sheet][index]["pct_nav"] = "-40"
    assert "pct_nav '-40' is negative" in _problems(data)


def test_a_negative_rating_bucket_cannot_offset_another() -> None:
    # By hand: buckets 150 and -50 sum to 100, inside 99 to 101; the -50 is refused instead.
    data = valid()
    data["Rating_Distribution"] = [
        {"rating_bucket": "B", "pct_nav": "150", "issuers": 5},
        {"rating_bucket": "Unrated", "pct_nav": "-50", "issuers": 1},
    ]
    assert _problems(data) == ["pct_nav '-50' is negative"]


def test_a_hidden_row_and_a_hidden_sheet_are_refused() -> None:
    # By hand: row 2 of Top_Holdings is hidden (one issue at its first cell); Maturity_Profile is
    # hidden whole (one issue for the sheet).
    def hide_row(book: openpyxl.Workbook) -> None:
        book["Top_Holdings"].row_dimensions[2].hidden = True

    def hide_sheet(book: openpyxl.Workbook) -> None:
        book["Maturity_Profile"].sheet_state = "hidden"

    assert _problems(valid(), hide_row) == ["row 2 holds hidden cells"]
    assert _problems(valid(), hide_sheet) == ["sheet Maturity_Profile is hidden"]
    raw = _workbook(valid())
    source = prepare_source(
        SourceRequest(source_id="portfolio", path="p.xlsx", media_type=MEDIA_TYPE), raw
    )
    assert portfolio_facts(source).top_holdings  # the visible workbook still yields its holdings
