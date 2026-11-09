"""Canonical adjusted EBITDA and period-absent add-backs (S13 A06/C04).

Expected values are derived by hand in the comments, not with the production code.
"""

from decimal import Decimal

from deploy_vii.canonical_kpis import _canonical_frame
from deploy_vii.model._cells import ABSENT
from deploy_vii.model.frame import Cell
from deploy_vii.model.statements import _income

# FY2023: revenue 100, COGS -40, opex (with D&A) -30, D&A -10, no stated EBITDA or adjusted
# EBITDA. Gross profit 60, EBIT 60 - 30 = 30, EBITDA 30 + 10 = 40.
LINES = {
    "revenue": Cell(Decimal(100)),
    "cogs": Cell(Decimal(-40)),
    "opex_total": Cell(Decimal(-30)),
    "da": Cell(Decimal(-10)),
}


def _adjusted(addbacks: dict[str, Cell]) -> tuple[Cell, Cell]:
    """(canonical adjusted EBITDA, Model statement adjusted EBITDA) for one column."""
    accounts = {"acct:revenue": LINES["revenue"], "acct:cogs": LINES["cogs"], **addbacks}

    def get(key: str) -> Cell:
        return LINES.get(key, accounts.get(key, ABSENT))

    statement = {**LINES, **_income(get, accounts, frozenset())}
    frame = _canonical_frame({"FY:2023": accounts}, {"FY:2023": statement}, {})
    return frame["FY:2023"]["adjusted_ebitda"], statement["adjusted_ebitda"]


def test_an_add_back_with_no_row_in_the_column_adds_nothing() -> None:
    # Restructuring 5 here; acquisition costs disclosed only in FY2024 (NOT_SOURCED here).
    # Adjusted EBITDA 40 + 5 = 45, on the canonical register as in the Model statement.
    assert ABSENT.reason == "NOT_SOURCED"
    canonical, statement = _adjusted(
        {"addback:restructuring": Cell(Decimal(5)), "addback:acquisition_costs": ABSENT}
    )
    assert (canonical.value, canonical.reason) == (Decimal(45), None)
    assert statement.value == Decimal(45)
    assert canonical.note == "Reported value unavailable; derived from components"


def test_an_add_back_row_without_a_figure_leaves_the_value_missing() -> None:
    # A row for this column with no figure: the sum cannot be formed, and the note no longer
    # says the missing value was derived.
    canonical, statement = _adjusted(
        {"addback:restructuring": Cell(Decimal(5)), "addback:other": Cell(None, "NOT_STATED")}
    )
    assert canonical.value is None and statement.value is None
    assert canonical.note == "Reported value unavailable; components incomplete"


def test_only_period_absent_add_backs_give_ebitda() -> None:
    # Every add-back NOT_SOURCED: adjusted EBITDA is EBITDA, 40.
    canonical, statement = _adjusted({"addback:acquisition_costs": ABSENT})
    assert canonical.value == statement.value == Decimal(40)
