"""Focused controls for the mapping-only PDF header parser."""

from pathlib import Path

import pytest

from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow.financial_workflow import _header_columns, _HeaderPeriod, _mapped_columns
from deploy_workflow.pdf_headers import mapping_headers
from deploy_workflow.unit_maps import _header_verifies

ROOT = Path(__file__).parent / "fixtures" / "pdf_pages"


@pytest.mark.parametrize(
    "doc,page,first_data,kind,expected",
    [
        ("TDG", 105, 8, "BS", ("September 30, 2024 | September 30, 2023",)),
        ("CZR", 57, 6, "IS", ("FY 2025-12-31 | FY 2024-12-31 | FY 2023-12-31",)),
        (
            "VMO2Q3",
            6,
            15,
            "IS",
            (
                "Three Months Ended September 30 | Three Months Ended September 30 | Nine Months Ended September 30 | Nine Months Ended September 30",
                "2025 | 2024 | 2025 | 2024",
            ),
        ),
        (
            "VMO2Q3",
            9,
            15,
            "CFS",
            ("Nine Months Ended September 30 | Nine Months Ended September 30", "2025 | 2024"),
        ),
        ("SIX22", 94, 15, "IS", ("FY 2022-01-02 | FY 2020-12-31 | FY 2019-12-31",)),
    ],
)
def test_mapping_headers_recover_printed_periods(doc, page, first_data, kind, expected):
    text = (ROOT / doc / f"p{page:03}.txt").read_text()
    assert mapping_headers(text, first_data_line=first_data, statement=kind) == expected


def test_flow_header_without_printed_duration_refuses():
    text = "CONSOLIDATED STATEMENTS OF OPERATIONS\n\nDecember 31, 2024       December 31, 2023\nRevenue\n"
    assert mapping_headers(text, first_data_line=4, statement="IS") is None


def test_data_region_date_cannot_supply_header():
    text = "CONSOLIDATED STATEMENTS OF OPERATIONS\n\nRevenue\nYear Ended December 31, 2024\n"
    assert mapping_headers(text, first_data_line=3, statement="IS") is None


@pytest.mark.parametrize(
    "text",
    [
        "STATEMENTS OF OPERATIONS\nYear Ended February 31\n2024 2023\nRevenue\n",
        "STATEMENTS OF OPERATIONS\nYear Ended December 31\nJanuary 2, 2024 2023\nRevenue\n",
        "STATEMENTS OF CASH FLOWS\nNine months ended\nRevenue\n",
        "STATEMENTS OF CASH FLOWS\nThree months ended Nine months ended Twelve months ended\n2025 2024 2023 2022\nCash\n",
        "STATEMENTS OF OPERATIONS\nYear Ended December 31\n2024NoteX 2023\nRevenue\n",
    ],
)
def test_malformed_or_ambiguous_period_headers_refuse(text):
    assert mapping_headers(text, first_data_line=4, statement="IS") is None


def test_duplicate_declared_period_candidates_refuse_mapping():
    headers = ("FY 2024-12-31",)
    periods = [
        _HeaderPeriod.model_validate(
            {
                "period_id": "fy24",
                "fiscal_year": "2024",
                "fiscal_quarter": None,
                "period_type": "FY",
                "start_date": None,
                "end_date": "2024-12-31",
            }
        ),
        _HeaderPeriod.model_validate(
            {
                "period_id": "fy24-duplicate",
                "fiscal_year": "2024",
                "fiscal_quarter": None,
                "period_type": "FY",
                "start_date": None,
                "end_date": "2024-12-31",
            }
        ),
    ]
    assert _mapped_columns(headers, periods) is None


def test_duplicate_printed_year_columns_refuse_mapping():
    headers = ("FY 2024-12-31 | FY 2024-12-31",)
    period = _HeaderPeriod.model_validate(
        {
            "period_id": "fy24",
            "fiscal_year": "2024",
            "fiscal_quarter": None,
            "period_type": "FY",
            "start_date": None,
            "end_date": "2024-12-31",
        }
    )
    assert _mapped_columns(headers, [period]) is None


def test_report_banner_is_ignored_and_own_header_removal_refuses():
    path = ROOT / "VMO2Q3" / "p006.txt"
    original = path.read_text()
    changed_banner = original.replace("30 September 2025", "31 December 2099", 1)
    assert mapping_headers(changed_banner, first_data_line=15, statement="IS") == mapping_headers(
        original, first_data_line=15, statement="IS"
    )
    no_title_header = original.replace("Three months ended", "Three months", 1)
    no_title_header = no_title_header.replace("Nine months ended", "Nine months", 1)
    assert mapping_headers(no_title_header, first_data_line=15, statement="IS") is None
    header_lines = original.splitlines()
    for index in (10, 11, 12):
        header_lines[index] = ""
    without_unit_header = "\n".join(header_lines)
    assert mapping_headers(without_unit_header, first_data_line=15, statement="IS") is None


def test_continuation_page_does_not_borrow_another_pages_header():
    text = (ROOT / "CZR" / "p061.txt").read_text()
    own = "Years Ended December 31,"
    assert mapping_headers(text, first_data_line=5, statement="CFS") is not None
    assert mapping_headers(text.replace(own, "", 1), first_data_line=5, statement="CFS") is None


def test_pdf_balance_map_rejects_swapped_short_and_long_model_columns():
    text = (ROOT / "TDG" / "p105.txt").read_text()
    headings = mapping_headers(text, first_data_line=8, statement="BS")
    periods = [
        _HeaderPeriod.model_validate(
            {
                "period_id": period_id,
                "fiscal_year": year,
                "fiscal_quarter": None,
                "period_type": "PERIOD_END",
                "start_date": None,
                "end_date": end,
            }
        )
        for period_id, year, end in (
            ("tdg-2024", "2024", "2024-09-30"),
            ("tdg-2023", "2023", "2023-09-30"),
        )
    ]
    mapped = _mapped_columns(headings, periods)
    assert mapped == (frozenset(("tdg-2024",)), frozenset(("tdg-2023",)))
    assert _header_verifies(mapped, ("tdg-2024", "tdg-2023"))
    assert not _header_verifies(mapped, ("tdg-2023", "tdg-2024"))
    assert not _header_verifies(mapped, ("tdg-2024",))
    assert not _header_verifies(mapped, ("tdg-2024", "tdg-2023", "extra"))


def test_typed_report_metadata_cannot_supply_a_missing_unit_duration():
    text = (ROOT / "CZR" / "p057.txt").read_text()
    text = text.replace("Years Ended December 31,", "December 31,", 1)
    poisoned = "Annual report: Fiscal Years Ended\n" + text
    table = extract_statement_lines(poisoned, "page:57", "CZR")
    periods = [
        {
            "period_id": f"fy{year}",
            "fiscal_year": str(year),
            "fiscal_quarter": None,
            "period_type": "FY",
            "start_date": None,
            "end_date": f"{year}-12-31",
        }
        for year in (2025, 2024, 2023)
    ]
    assert _header_columns(table, {"periods": periods}, page_text=poisoned, statement="IS") is None


def test_unsupported_duration_prefix_cannot_be_matched_as_a_substring():
    text = (ROOT / "VMO2Q3" / "p009.txt").read_text()
    unsupported = text.replace("Nine months ended", "Twenty Three months ended", 1)
    periods = [
        {
            "period_id": f"q3-{year}",
            "fiscal_year": str(year),
            "fiscal_quarter": 3,
            "period_type": "QUARTER",
            "start_date": f"{year}-07-01",
            "end_date": f"{year}-09-30",
        }
        for year in (2025, 2024)
    ]
    table = extract_statement_lines(unsupported, "page:9", "VMO2Q3")
    assert (
        _header_columns(table, {"periods": periods}, page_text=unsupported, statement="CFS") is None
    )


def test_typed_report_banner_cannot_replace_balance_sheet_column_dates():
    text = (ROOT / "TDG" / "p105.txt").read_text()
    poisoned = "Report for Year Ended March 31, 2024\n" + text
    periods = [
        {
            "period_id": period_id,
            "fiscal_year": year,
            "fiscal_quarter": None,
            "period_type": "PERIOD_END",
            "start_date": None,
            "end_date": end,
        }
        for period_id, year, end in (
            ("mar24", "2024", "2024-03-31"),
            ("sep24", "2024", "2024-09-30"),
            ("sep23", "2023", "2023-09-30"),
        )
    ]
    table = extract_statement_lines(poisoned, "page:105", "TDG")
    assert _header_columns(table, {"periods": periods}, page_text=poisoned, statement="BS") == (
        frozenset(("sep24",)),
        frozenset(("sep23",)),
    )


def test_month_and_year_header_does_not_read_the_year_as_a_day():
    # S11-C07. By hand: "June 2024" names no day; the "20" of 2024 is not June 20. The header
    # maps to nothing (fails closed), while "30 June" with years below still maps to June 30.
    text = "Balance sheet\nJune 2024  June 2023\nAssets\nCash 1 2\n"
    assert mapping_headers(text, first_data_line=4, statement="BS") is None
    spaced = "Balance sheet\nJune   2024      June 2023\nAssets\nCash 1 2\n"
    assert mapping_headers(spaced, first_data_line=4, statement="BS") is None
    dated = "Balance sheet\nAs at 30 June\n2024  2023\nCash 1 2\n"
    assert mapping_headers(dated, first_data_line=4, statement="BS") == (
        "June 30, 2024 | June 30, 2023",
    )
