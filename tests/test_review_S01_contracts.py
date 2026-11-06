"""S01 review: contract shapes for a balance-sheet period and the debt adjustment type.

Synthetic values; expectations are literal."""

from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from deploy_vii.contracts import Citation
from deploy_vii.financial_contracts import FinancialPeriod
from deploy_vii.model.registers import DEBT_ADJUSTMENT

CITATION = Citation(source_id="s1", source_sha256="a" * 64, locator="page:3", quote="Balance")


def _period(**changes: Any) -> FinancialPeriod:
    fields: dict[str, Any] = {
        "period_id": "bs24",
        "fiscal_year": "FY2024",
        "fiscal_quarter": None,
        "period_type": "PERIOD_END",
        "start_date": None,
        "end_date": date(2024, 12, 31),
        "day_count": None,
        "audit_status": "audited",
        "currency": "USD",
        "unit": "MILLIONS",
        "accounting_basis": "US GAAP",
        "entity_perimeter": "Group consolidated",
        "citations": (CITATION,),
    }
    return FinancialPeriod(**{**fields, **changes})


def test_a_balance_sheet_instant_needs_no_limitation_for_its_start_date() -> None:
    period = _period()
    assert period.start_date is None and period.end_date == date(2024, 12, 31)
    assert period.limitation is None


def test_a_balance_sheet_instant_keeps_a_stated_limitation() -> None:
    text = "Point-in-time balance sheet date, not a duration"
    assert _period(limitation=text).limitation == text


@pytest.mark.parametrize(
    "changes",
    [
        {"end_date": None},  # an instant with no date at all
        {"period_type": "FY", "end_date": date(2024, 12, 31)},
        {"period_type": "LTM"},
        {"period_type": "YTD", "fiscal_quarter": 2},
        {"period_type": "FY", "start_date": date(2024, 1, 1), "end_date": None},
    ],
)
def test_other_missing_dates_still_require_a_limitation(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="missing period dates require a limitation"):
        _period(**changes)


def test_debt_adjustment_constant_is_the_cp1_facility_type() -> None:
    assert DEBT_ADJUSTMENT == "DEBT ADJUSTMENT"
