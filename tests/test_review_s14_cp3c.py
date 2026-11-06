"""S14 review fixes for CP-3C: the facility-currency amortisation, the minimum-cash limitation
and the calendar month arithmetic. Expected texts and dates are literal.
"""

from dataclasses import replace
from datetime import date

import pytest
import test_method_cp3c as t

from deploy_workflow.owners import cp3c

FX = "Not calculable: facility term-loan is in EUR, not USD; no FX conversion is applied"
FX_LINE = (
    "Facility term-loan is denominated in EUR; maturity-wall totals and shares are not "
    "calculated because no FX conversion is applied."
)


def _eur_inputs(amortisation_currency: str) -> cp3c.Cp3cInputs:
    row = t._positive_row()
    wall = (replace(row, principal=t._gone(row.principal, FX)),)
    terms = t._positive_terms()
    amortisation = replace(terms.annual_amortisation, currency=amortisation_currency)
    eur = replace(terms, currency="EUR", annual_amortisation=amortisation)
    return t._positive_with(eur, wall=wall)


def test_a_facility_amortisation_in_its_own_currency_takes_the_fx_gap_path() -> None:
    """adv S14 cp3c.py:912: CP-1 states a EUR facility's amortisation in EUR; CP-3C composes
    the documented FX gap instead of raising on the amortisation's currency."""
    result = cp3c.compute(_eur_inputs("EUR"))
    assert FX_LINE in result.own_limitations
    payable = t._cells_of(result)["T3D.2.r01"]
    assert payable.status == "missing" and payable.amount is None


def test_an_amortisation_in_a_third_currency_still_raises() -> None:
    with pytest.raises(ValueError, match="term-loan.annual_amortisation: currency 'GBP' is not"):
        cp3c.compute(_eur_inputs("GBP"))


@pytest.mark.parametrize(
    ("status", "line"),
    [
        (
            "conflicting",
            (
                "Minimum cash is conflicting in CP-2D, so resources at maturity and the refinancing "
                "need are not calculated."
            ),
        ),
        (
            "not_applicable",
            (
                "Minimum cash is not applicable in CP-2D, so resources at maturity and the "
                "refinancing need are not calculated."
            ),
        ),
    ],
)
def test_the_minimum_cash_limitation_names_an_unsettled_status(status: str, line: str) -> None:
    """cr S14 cp3c.py:1767: the limitation agrees with the cells' reason, not 'not assessed'."""
    inputs = t._inputs("positive")
    minimum = t._unsettled(inputs.cp2d.minimum_cash, status)
    result = cp3c.compute(replace(inputs, cp2d=replace(inputs.cp2d, minimum_cash=minimum)))
    assert line in result.own_limitations
    assert not any("Minimum cash was not assessed" in x for x in result.own_limitations)
    reason = f"Not calculable: minimum cash is {status.replace('_', ' ')}"
    resources = t._cells_of(result)["T3D.2.r02"]
    assert resources.reason == reason


def test_the_missing_and_known_minimum_cash_lines_are_unchanged() -> None:
    known = cp3c.compute(t._inputs("positive")).own_limitations
    assert "Minimum cash is an analyst assumption, not a source figure." in known
    missing = cp3c.compute(t._inputs("gap_minimum_cash")).own_limitations
    assert (
        "Minimum cash was not assessed, so resources at maturity and the refinancing need are "
        "not calculated." in missing
    )


@pytest.mark.parametrize(
    ("start", "months", "end"),
    [
        (date(2025, 12, 31), 2, date(2026, 2, 28)),
        (date(2023, 12, 31), 2, date(2024, 2, 29)),
        (date(2099, 12, 31), 2, date(2100, 2, 28)),
        (date(1999, 12, 31), 2, date(2000, 2, 29)),
        (date(2025, 1, 31), 3, date(2025, 4, 30)),
        (date(2025, 12, 31), 6, date(2026, 6, 30)),
        (date(2025, 12, 31), 0, date(2025, 12, 31)),
    ],
)
def test_add_months_clamps_to_the_month_end(start: date, months: int, end: date) -> None:
    assert cp3c._add_months(start, months) == end


def test_the_facility_position_is_wall_position() -> None:
    """The tested `wall_position` is the rule `_facility` applies (31 Dec 2025 to 30 Jun 2026 is
    6 months; inside a 6-month horizon on the day, outside a 5-month one)."""
    d0, maturity = date(2025, 12, 31), date(2026, 6, 30)
    assert cp3c.wall_position(balance_date=d0, maturity=maturity, horizon_months=6) == (6, True)
    assert cp3c.wall_position(balance_date=d0, maturity=maturity, horizon_months=5) == (6, False)
