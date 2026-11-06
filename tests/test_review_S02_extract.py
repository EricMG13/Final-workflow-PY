"""Review S02 (statement extraction): header years per table, printed negative and currency
forms, unreadable rows kept in `omitted`, and label candidates from the returned label.
Expected values are literal readings of the printed pages."""

from decimal import Decimal

import pytest

from deploy_vii.statement_extract import OmittedLine, extract_statement_lines

COLUMNS = "                                          2025          2024"
MARKER_ROW = "Cash and cash equivalents  (1)           1,234         1,100"


@pytest.mark.parametrize("title", ["(In millions)", "December 31, 2025 and 2024 (In millions)"])
def test_a_dated_title_does_not_double_the_header_years(title: str) -> None:
    page = f"CONSOLIDATED BALANCE SHEETS\n{title}\n\n{COLUMNS}\n{MARKER_ROW}\nInventories  2,000  1,900"
    cash = extract_statement_lines(page, "page:1").lines[0]
    assert cash.raw_values == ("1,234", "1,100")
    assert cash.values == (Decimal(1234), Decimal(1100))
    assert cash.flags == ("footnote_marker",)


def test_a_second_table_on_the_page_gets_its_own_header_block() -> None:
    page = "                              2025      2024      2023\nRevenue                       1,000       900       800\nCost of sales                   600       500       400\n\n                                        2025      2024\nCash and cash equivalents      (1)     1,234     1,100\nRestricted cash                          50        40"
    table = extract_statement_lines(page, "page:1")
    assert table.headers == ("                              2025      2024      2023",)
    assert [(x.label, x.raw_values, x.flags) for x in table.lines] == [
        ("Revenue", ("1,000", "900", "800"), ()),
        ("Cost of sales", ("600", "500", "400"), ()),
        ("Cash and cash equivalents", ("1,234", "1,100"), ("footnote_marker",)),
        ("Restricted cash", ("50", "40"), ()),
    ]
    cash = table.lines[2]
    assert cash.values == (Decimal(1234), Decimal(1100))


def test_a_second_table_marker_under_its_first_year_is_flagged_not_silent() -> None:
    page = "                              2025      2024      2023\nRevenue                       1,000       900       800\n\n                              2025      2024\nCash and cash equivalents      (1)     1,234     1,100"
    cash = extract_statement_lines(page, "page:1").lines[1]
    assert cash.raw_values == ("(1)", "1,234", "1,100")
    assert cash.flags == ("more_values_than_header_years",)


def test_a_month_subheading_inside_a_table_keeps_the_table_header() -> None:
    page = "                              2025      2024      2023\nRevenue                       1,000       900       800\nBalance at December 31:\nOther  (1)                      10         9         8"
    other = extract_statement_lines(page, "page:1").lines[1]
    assert (other.raw_values, other.flags) == (("10", "9", "8"), ("footnote_marker",))


HEADER3 = "                               2025       2024       2023"


@pytest.mark.parametrize(
    ("row", "raw", "values", "currency"),
    [
        (
            "Net loss                        -45        -30        -12",
            ("-45", "-30", "-12"),
            ("-45", "-30", "-12"),
            (False, False, False),
        ),
        (
            "Other expense                  −450       −300       −120",
            ("−450", "−300", "−120"),
            ("-450", "-300", "-120"),
            (False, False, False),
        ),
        (
            "Foreign exchange               -500        900        800",
            ("-500", "900", "800"),
            ("-500", "900", "800"),
            (False, False, False),
        ),
        (
            "Impairment                    ($120)     ($80)       ($5)",
            ("(120)", "(80)", "(5)"),
            ("-120", "-80", "-5"),
            (True, True, True),
        ),
        (
            "Loss on disposal            (1,234 )     (1,100 )     (900 )",
            ("(1,234 )", "(1,100 )", "(900 )"),
            ("-1234", "-1100", "-900"),
            (False, False, False),
        ),
        (
            "Revenue                      1,234 €      1,100 €     1,000 €",
            ("1,234", "1,100", "1,000"),
            ("1234", "1100", "1000"),
            (True, True, True),
        ),
        (
            "Tax                           1,234-        1,100-       900-",
            ("1,234-", "1,100-", "900-"),
            ("-1234", "-1100", "-900"),
            (False, False, False),
        ),
        (
            "Adjustment                    –1.5        2.25       —",
            ("–1.5", "2.25", "—"),
            ("-1.5", "2.25", None),
            (False, False, False),
        ),
    ],
)
def test_printed_negative_and_currency_forms_are_read(
    row: str, raw: tuple[str, ...], values: tuple[str | None, ...], currency: tuple[bool, ...]
) -> None:
    table = extract_statement_lines(f"{HEADER3}\n{row}", "page:1")
    (line,) = table.lines
    assert line.raw_values == raw
    assert line.values == tuple(None if v is None else Decimal(v) for v in values)
    assert line.currency_values == currency
    assert line.flags == ()
    assert table.omitted == ()


def test_a_trailing_euro_belongs_to_the_number_on_its_left() -> None:
    header = "                                   2025          2024        2023"
    table = extract_statement_lines(f"{header}\nRevenue   1,234 €  9   1,100", "page:1")
    (line,) = table.lines
    assert line.raw_values == ("1,234", "9", "1,100")
    assert line.currency_values == (True, False, False)


def test_a_dollar_before_a_wide_gap_still_prefixes_the_number_on_its_right() -> None:
    table = extract_statement_lines(f"{HEADER3}\nRevenue   $   1,234   $   1,100   900", "p")
    (line,) = table.lines
    assert line.raw_values == ("1,234", "1,100", "900")
    assert line.currency_values == (True, True, False)


def test_rows_the_rules_still_cannot_read_are_omitted_not_dropped() -> None:
    page = "                                   2025          2024\nEffective tax rate             21.5%         20.9%\nMargin                          n/m          12%\nRevenue                       1,200         1,000\nIn 2025 we sold 1,234 units and 1,100 the year before.\n                     June 30,      December 31,\nthe company reported revenue of      in fiscal 2025 the"
    table = extract_statement_lines(page, "page:1")
    assert [line.label for line in table.lines] == ["Revenue"]
    assert table.omitted == (
        OmittedLine(line_no=2, text="Effective tax rate             21.5%         20.9%"),
        OmittedLine(line_no=3, text="Margin                          n/m          12%"),
    )


def test_label_candidates_follow_the_returned_label() -> None:
    page = "                        Notes        2025      2024\nGoodwill                7 and 9     1,200     1,100\nRevenue                 3                     $1,100"
    goodwill, revenue = extract_statement_lines(page, "page:1").lines
    assert goodwill.label == "Goodwill"
    assert [(p.line_no, p.text) for p in goodwill.label_candidates] == [(2, "Goodwill")]
    assert revenue.label == "Revenue 3"
    assert [(p.line_no, p.text) for p in revenue.label_candidates] == [(3, "Revenue 3")]
