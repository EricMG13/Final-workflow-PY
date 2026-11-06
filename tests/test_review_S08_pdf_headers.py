"""S08 review regressions for the PDF period-header parser (Q4 mixed headers, malformed dates)."""

import pytest

from deploy_workflow.pdf_headers import mapping_headers

Q4 = (
    (
        "Three Months Ended December 31 | Three Months Ended December 31 | "
        "Year Ended December 31 | Year Ended December 31"
    ),
    "2024 | 2023 | 2024 | 2023",
)


@pytest.mark.parametrize("header", [
    "Three Months Ended December 31,      Year Ended December 31,\n2024   2023   2024   2023",
    "Three Months Ended      Year Ended\nDecember 31,      December 31,\n2024   2023   2024   2023",
])
def test_q4_release_maps_quarter_and_year_columns_separately(header):
    text = f"CONSOLIDATED STATEMENTS OF OPERATIONS\n{header}\nRevenue  1  2  3  4\n"
    first = text.count("\n")
    assert mapping_headers(text, first_data_line=first, statement="IS") == Q4


def test_year_only_header_still_maps_fiscal_years():
    text = "STATEMENTS OF OPERATIONS\nYear Ended December 31,\n2024   2023\nRevenue  1  2\n"
    assert mapping_headers(text, first_data_line=4, statement="IS") == (
        "FY 2024-12-31 | FY 2023-12-31",
    )


def test_flow_header_with_out_of_range_years_refuses_without_raising():
    text = "STATEMENTS OF OPERATIONS\nYear Ended\nDecember 31, 2150   December 31, 2149\nRevenue  1  2\n"
    assert mapping_headers(text, first_data_line=4, statement="IS") is None


def test_balance_sheet_with_out_of_range_years_keeps_complete_dates():
    text = "BALANCE SHEETS\nDecember 31, 2150   December 31, 2149\nCash  1  2\n"
    assert mapping_headers(text, first_data_line=3, statement="BS") == (
        "December 31, 2150 | December 31, 2149",
    )


@pytest.mark.parametrize("header", [
    "Three Months Ended June 31,      Year Ended June 31,\n2024   2023   2024   2023",
    "Six months ended 31 September\n2024   2023",
])
def test_span_header_with_impossible_end_date_refuses(header):
    text = f"STATEMENTS OF OPERATIONS\n{header}\nRevenue  1  2  3  4\n"
    assert mapping_headers(text, first_data_line=text.count("\n"), statement="IS") is None
