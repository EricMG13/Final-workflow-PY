"""Review S04: the run-text bare-figure guard (`deploy_vii.prose`).

Synthetic regressions over literal strings; expected tokens are written by hand.
"""

import pytest

from deploy_vii import prose


@pytest.mark.parametrize(
    ("text", "figures"),
    [
        # A year-shaped amount after a currency sign or code, or before a magnitude word, is an
        # amount, not a period label (statement_extract excludes `$`-prefixed years the same way).
        ("Revenue was $2050 million in the year.", ("$2050",)),
        ("Revenue was $ 2050 million.", ("2050",)),
        ("Debt of USD 2045 million rose.", ("2045",)),
        ("EBITDA fell to EUR 2000 million.", ("2000",)),
        ("Spreads widened 1950 bps.", ("1950",)),
        ("Sales reached 2010 Million.", ("2010",)),
        # `N of M` is a pack-coverage label only with a pack-structure noun.
        ("The issuer repaid 400 of 500 million of notes.", ("400", "500")),
        ("Leverage is 3 of 5 turns.", ("3", "5")),
        ("Covenant breached in 3 of 4 quarters.", ("3", "4")),
        ("Two classes: 2 of 3 facilities matured.", ("2", "3")),
        # An SEC file-number shape needs an SEC prefix; any other `NNN-NNNNN` is a figure.
        ("Revenue of 100-25000 units.", ("100-25000",)),
    ],
)
def test_amounts_shaped_like_labels_are_bare_figures(text: str, figures: tuple[str, ...]) -> None:
    assert prose.bare_figures(text) == figures


@pytest.mark.parametrize(
    "text",
    [
        "Read 195 of 195 pages.",
        "The pack covers 12 of 14 located spans and 3 of 3 sources.",
        "Commission file number 001-36629.",
        "Registration 333-12345 and BDC file 814-00663.",
        "Fiscal 2025 revenue declined; notes due 2032.",
        "In 2026, the issuer refinanced.",
        "Quote dated 09 January 2026.",
        "Quote dated January 09, 2026.",
        "Quote dated 9 January 2026 and June 30, 2026.",
        "The 6.50% notes due 2032 and Term Loan B-2.",
        "The EUR 2027 notes and the USD 2029 bonds.",
    ],
)
def test_labels_stay_labels(text: str) -> None:
    assert prose.bare_figures(text) == ()


def test_a_name_never_covers_part_of_a_longer_token() -> None:
    assert prose.bare_figures("Revenue of 3Mn", names=("3M",)) == ("3Mn",)
    assert prose.bare_figures("3M reported; 3M's plants ran.", names=("3M",)) == ()


def test_a_year_before_an_unrelated_capital_letter_stays_a_period() -> None:
    assert prose.bare_figures("In 2026 M&A activity rose; by 2027 X-ray sales grew.") == ()
