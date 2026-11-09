"""The run-text figure guard (decision 0005 MC-2): S13 A04/C07 and A05.

Expected values are written out by hand from the rule text, not computed with `prose`.
"""

from decimal import Decimal

import pytest

from deploy_vii import prose
from deploy_vii.contracts import Fact

# --- A04/C07: "N of M", years before a quantity word, numbers in words ----------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # "N of M" is a coverage label only with a pack noun after it.
        ("Covenant headroom was breached in 3 of 4 quarters.", ("3", "4")),
        ("The reader read 195 of 195 pages.", ()),
        ("It located 12 of 14 sources and 3 of 3 located spans.", ()),
        ("Amendment No. 5 of 2025 applies.", ("5",)),
        # A year followed by a quantity word is a figure, not a period label.
        ("EBITDA margin fell by 2024 basis points.", ("2024",)),
        ("Spreads widened 2024 bps.", ("2024",)),
        ("Margin rose 2025 %.", ("2025",)),
        ("Revenue in 2024 was flat against 2023.", ()),
        ("The 7.125% senior secured notes due 2032 rank first.", ()),
        # A number in words with a quantity word, "-fold" or a multiplying verb is a figure.
        (
            "Leverage rose to seven times EBITDA and revenue halved.",
            ("seven times", "halved"),
        ),
        ("Costs rose twenty-five percent.", ("twenty-five percent",)),
        ("Debt grew threefold while capex doubled.", ("threefold", "doubled")),
        ("Ten per cent of revenue is hedged.", ("Ten per cent",)),
        ("One of the notes carries a one-time fee.", ()),
        # Whitespace and hyphen variants (confidence review).
        ("Margin fell by 2024  basis points.", ("2024",)),
        ("Spreads widened 2024\u00a0bps.", ("2024",)),
        ("Leverage rose to seven  times EBITDA.", ("seven  times",)),
        ("A seven-times multiple.", ("seven-times",)),
        ("Costs rose twenty  five percent.", ("twenty  five percent",)),
        ("The 2024\nresults were flat.", ()),
        # Reading order across numeric and word figures.
        ("Revenue halved in 3 of 4 quarters.", ("halved", "3", "4")),
    ],
)
def test_bare_figures(text: str, expected: tuple[str, ...]) -> None:
    assert prose.bare_figures(text) == expected


def test_a_supplied_name_covers_a_number_word() -> None:
    # The issuer name is a supplied name: its words are not a figure.
    assert prose.bare_figures("Seven Times Media reported.", names=("Seven Times Media",)) == ()
    assert prose.bare_figures("Seven Times Media reported.") == ("Seven Times",)


def test_check_reports_each_bypass_as_a_bare_figure() -> None:
    found = prose.check(
        "Covenant headroom was breached in 3 of 4 quarters; margin fell by 2024 basis points.",
        refs=(),
        gaps=(),
    )
    assert found == ("Bare figure: 3", "Bare figure: 4", "Bare figure: 2024")


# --- A05: a fiscal year label beside a figure reference -------------------------------------


def _fact(fact_id: str, period: str | None, amount: str = "812") -> Fact:
    return Fact(
        fact_id=fact_id,
        label="Revenue",
        amount=Decimal(amount),
        unit="MILLIONS",
        currency="USD",
        scale=Decimal(1000000),
        period=period,
        calculation_id=f"calc-{fact_id}",
    )


BOUND = prose.bind(
    [
        _fact("rev-fy2023", "FY2023: 2023-01-01 to 2023-12-31"),
        _fact("rev-fy2024", "FY2024: 2023-10-01 to 2024-09-30", "900"),
        _fact("rev-fy25", "FY25"),
        _fact("nd-2024", "2024-12-31"),
        _fact("plan", "FY2025-FY2028"),
        _fact("undated", "LTM"),
        Fact(
            fact_id="lev-fy28",
            label="Leverage",
            status="missing",
            period="FY2028",
            limitation="Not forecast",
        ),
        Fact(fact_id="note", label="Business", text="A distributor", citations=()),
    ]
)


def _wrong(label: str) -> str:
    return (
        f"Period label {label} is not the period of a figure in its clause "
        "(rev-fy2023 is FY2023: 2023-01-01 to 2023-12-31)"
    )


def test_a_fiscal_label_beside_another_periods_figure_is_refused() -> None:
    # rev-fy2023 spans 2023 only; FY2025 and FY2024 name neither, and a comma does not end the
    # clause, so both labels are refused (the finding's text, S13 A05).
    text = "FY2025 revenue reached {rev-fy2023}, up from FY2024."
    assert prose.issues(text, BOUND) == (_wrong("FY2025"), _wrong("FY2024"))


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("In FY2025, revenue reached {rev-fy2023}.", "FY2025"),
        ("Revenue reached {rev-fy2023} in fiscal 2025.", "fiscal 2025"),
        ("Fiscal year 2025 revenue was {rev-fy2023}.", "Fiscal year 2025"),
        ("CY2022 revenue was {rev-fy2023}.", "CY2022"),
        ("FY22 revenue was {rev-fy2023}.", "FY22"),
        ("FY-2025 revenue was {rev-fy2023}.", "FY-2025"),
        ("Fiscal  2025 revenue was {rev-fy2023}.", "Fiscal  2025"),
        # A chip whose fact has no period does not switch the check off.
        ("FY2025 revenue reached {rev-fy2023} [note].", "FY2025"),
        # Stricter than a phrase-level reading: another year in the clause is refused too.
        ("Revenue was {rev-fy2023} in FY2023, against FY2025 guidance.", "FY2025"),
    ],
)
def test_each_wrong_fiscal_label_in_the_clause_is_refused(text: str, label: str) -> None:
    assert prose.issues(text, BOUND) == (_wrong(label),)


@pytest.mark.parametrize(
    "text",
    [
        "FY2023 revenue reached {rev-fy2023}.",
        # The label after the figure, and the calculation id as the reference.
        "Revenue reached {calc-rev-fy2023} in FY2023.",
        # A fiscal year ending September 2024 spans 2023 and 2024: either year passes.
        "FY2024 revenue was {rev-fy2024}.",
        "FY2023 revenue was {rev-fy2024}.",
        # Two-digit labels on either side.
        "FY25 revenue was {rev-fy25} and FY2025 closed.",
        "In FY2025 revenue was {rev-fy25}.",
        # Two figures, two labels, each label the period of one of them.
        "Revenue rose from {rev-fy2023} in FY2023 to {rev-fy2024} in FY2024.",
        # A range period spans every year in it.
        "The plan reaches {plan} by FY2027.",
        # A balance date: the year of the date.
        "FY2024 net debt was {nd-2024}.",
        # A figure whose period names no year: the clause cannot be compared.
        "FY2030 revenue was {undated} against {rev-fy2023}.",
        # A bare year or a date is not a fiscal label (a maturity sits beside amounts).
        "Net debt of {nd-2024} includes notes due 2031.",
        # A clause with no figure is not compared.
        "FY2030 is outside the plan; revenue was {rev-fy2023}.",
        # A gap chip counts with its own period (the CP-2G downside template).
        "Revenue is {rev-fy2023} in FY2023 and [lev-fy28] in FY2028, and FY2023 closed.",
    ],
)
def test_a_fiscal_label_matching_a_figure_passes(text: str) -> None:
    assert prose.issues(text, BOUND) == ()


def test_each_label_needs_a_figure_of_its_own_period() -> None:
    # FY2023 matches rev-fy2023, FY2026 matches neither figure in the clause.
    text = "Revenue rose from {rev-fy2023} in FY2023 to {rev-fy2024} in FY2026."
    assert prose.issues(text, BOUND) == (
        (
            "Period label FY2026 is not the period of a figure in its clause "
            "(rev-fy2023 is FY2023: 2023-01-01 to 2023-12-31; "
            "rev-fy2024 is FY2024: 2023-10-01 to 2024-09-30)"
        ),
    )


# --- Second-model review: hyphen and fiscal-year-end variants (hand-derived) ----------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # A year joined to a quantity word by a hyphen is as much a figure as one set apart.
        ("A 2024-basis-point rise.", ("2024-basis-point",)),
        ("Spreads moved 2024-bp.", ("2024-bp",)),
        ("A 2024 basis-point rise.", ("2024",)),
        ("A 2024 per-cent rise.", ("2024",)),
        # Controls: an ISO date and a year range are labels, not figures.
        ("Results to 2026-06-30 were flat.", ()),
        ("Notes due 2031-2033 rank first.", ()),
    ],
)
def test_bare_figures_hyphen_variants(text: str, expected: tuple[str, ...]) -> None:
    assert prose.bare_figures(text) == expected


YEAR_ENDS = prose.bind(
    [
        # Target's fiscal 2023 ended 2024-02-03: a balance date in the year after its label.
        _fact("cash-fy2023", "Balance at 2024-02-03"),
        _fact("rev-12m", "Twelve months to 2026-03-31"),
        _fact("rev-label", "FY2024"),
        _fact("rev-ltm", "LTM Q4 25: 2025-01-01 to 2025-12-31"),
    ]
)


@pytest.mark.parametrize(
    ("text", "ok"),
    [
        # The fiscal year closing 2024-02-03 is FY2023 by start year, FY2024 by end year.
        ("FY2023 cash was {cash-fy2023}.", True),
        ("FY2024 cash was {cash-fy2023}.", True),
        ("FY2025 cash was {cash-fy2023}.", False),
        ("FY2022 cash was {cash-fy2023}.", False),
        # Twelve months to 2026-03-31 are FY2025 (start year) or FY2026 (end year).
        ("FY2025 revenue was {rev-12m}.", True),
        ("FY2026 revenue was {rev-12m}.", True),
        ("FY2027 revenue was {rev-12m}.", False),
        ("FY2024 revenue was {rev-12m}.", False),
        # An explicit fiscal label is exact: nothing widens FY2024.
        ("FY2024 revenue was {rev-label}.", True),
        ("FY2023 revenue was {rev-label}.", False),
        # A window with both dates is exact: January to December 2025 is not FY2024.
        ("FY2025 revenue was {rev-ltm}.", True),
        ("FY2024 revenue was {rev-ltm}.", False),
    ],
)
def test_a_lone_date_period_admits_the_fiscal_year_it_closes(text: str, ok: bool) -> None:
    assert (prose.issues(text, YEAR_ENDS) == ()) is ok
