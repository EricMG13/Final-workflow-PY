"""CP-1 KPI period identity: a trailing ratio states the basis its operands use.

A QUARTER column's twelve-month ratios (leverage, coverage, debt ratios) read the rolling
four-quarter cells, so `period_basis_id` must be the rolling basis, never the single quarter's.
Fixture: Q3 2025 quarter EBITDA 25, rolling four-quarter (LTM) EBITDA 100, total debt 500.
Expected values are hand-derived: total leverage = 500 / 100 = 5 (not 500 / 25 = 20).
"""

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

import deploy_vii.canonical_kpis as ck
from deploy_vii.financial_model import _basis_id
from deploy_vii.model.frame import Cell, Column

QUARTER = Column("Q:q3-2025", "QUARTER", "Q3 25", "q3-2025", "2025", "2025-09-30", 92, None)
FY = Column("FY:fy-2025", "FY", "FY25", "fy-2025", "2025", "2025-12-31", 365, None)


def _cells(ebitda: str, debt: str) -> dict[str, Cell]:
    cells = {key: Cell(None, "NOT_SOURCED") for key in ck._SCALARS}
    cells["ebitda"] = Cell(Decimal(ebitda), basis="REPORTED")
    cells["total_debt"] = Cell(Decimal(debt), basis="REPORTED")
    return cells


@pytest.fixture
def rows(monkeypatch: pytest.MonkeyPatch) -> dict[tuple[str, str], Any]:
    monkeypatch.setattr(ck, "normalize_facilities", lambda book: ())
    monkeypatch.setattr(ck, "_evidence", lambda book, normalizations: {})
    frame = {QUARTER.column_id: _cells("25", "500"), FY.column_id: _cells("100", "500")}
    rolling = {QUARTER.column_id: _cells("100", "500")}
    book = SimpleNamespace(currency="USD", unit="MILLIONS")
    result = ck._kpi_rows((QUARTER, FY), frame, rolling, book, {})  # type: ignore[arg-type]
    return {(row.display_basis_id, row.key): row for row in result}


def test_quarter_trailing_ratio_states_the_rolling_basis(rows: dict[Any, Any]) -> None:
    quarter, rolling = _basis_id(QUARTER), _basis_id(QUARTER, True)
    leverage = rows[quarter, "total_leverage_reported"]
    assert leverage.value.amount == Decimal(5)  # 500 / 100 (LTM EBITDA)
    assert leverage.display_basis_id == quarter  # still shown in the Q3 25 column
    assert leverage.period_basis_id == rolling  # but stated over the rolling four quarters
    operand_bases = {o.value_id for o in leverage.denominator.operands}
    assert operand_bases == {ck._value_id(rolling, "ebitda")}


def test_quarter_own_values_keep_the_quarter_basis(rows: dict[Any, Any]) -> None:
    quarter = _basis_id(QUARTER)
    ebitda = rows[quarter, "ebitda"]
    assert ebitda.value.amount == Decimal(25)
    assert ebitda.period_basis_id == quarter


def test_fy_ratio_keeps_its_own_basis(rows: dict[Any, Any]) -> None:
    fy = _basis_id(FY)
    leverage = rows[fy, "total_leverage_reported"]
    assert leverage.value.amount == Decimal(5)  # 500 / 100 (FY EBITDA)
    assert leverage.period_basis_id == fy
