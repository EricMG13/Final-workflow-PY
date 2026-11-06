"""S01 review: a frame cell built from others keeps why they are missing, normalised or partial.

Synthetic registers (no issuer, no model response): each expectation is a literal written from
the rule `_cells.calc` states (a missing part's note, `sign normalised`, then the cell's own),
not read back from production output.
"""

from decimal import Decimal

from deploy_vii.model import history
from deploy_vii.model.frame import Frame, SourceRef
from deploy_vii.model.registers import (
    AccountRow,
    AddbackRow,
    Cp1Registers,
    FacilityRow,
    PeriodRow,
)
from deploy_vii.model.statements import statement_frame

UNSPANNED = "components do not span the period"


def _period(
    period_id: str, kind: str, start: str, end: str, days: int, **extra: object
) -> PeriodRow:
    quarter = extra.get("quarter")
    components = extra.get("components", ())
    assert isinstance(components, tuple)
    return PeriodRow(
        period_id,
        "FY" + end[:4],
        quarter if isinstance(quarter, str) else None,
        kind,
        start,
        end,
        days,
        "USD",
        "MILLIONS",
        components,
    )


def _account(metric: str, period_id: str, value: str) -> AccountRow:
    return AccountRow(
        metric,
        period_id,
        Decimal(value),
        "VERIFIED",
        SourceRef("s1", f"{metric}@{period_id}", value),
    )


def _registers(
    periods: list[PeriodRow],
    accounts: list[AccountRow],
    facilities: tuple[FacilityRow, ...] = (),
    addbacks: tuple[AddbackRow, ...] = (),
) -> Cp1Registers:
    return Cp1Registers(
        tuple(periods), tuple(accounts), addbacks, (), (), facilities, (), "USD", "MILLIONS"
    )


def _frame(regs: Cp1Registers, exclude_unrealised: bool = False) -> Frame:
    columns = history.historical_columns(regs)
    accounts = history.account_frame(regs, columns)
    return statement_frame(accounts, columns, regs, exclude_unrealised)


FY = [_period("fy24", "FY", "2024-01-01", "2024-12-31", 366)]
# An FY whose two components leave 30 June uncovered: every derived FY figure is unspanned.
GAPPED = [
    _period("h1", "YTD", "2024-01-01", "2024-06-29", 181, quarter="2"),
    _period("h2", "QUARTER", "2024-07-01", "2024-12-31", 184, quarter="4"),
    _period("fy24", "FY", "2024-01-01", "2024-12-31", 366, components=("h1", "h2")),
]


def test_income_sums_keep_sign_normalised_from_a_positive_cost() -> None:
    regs = _registers(
        FY,
        [
            _account("revenue", "fy24", "100"),
            _account("cogs", "fy24", "60"),  # written positive: read as -60
            _account("gross_profit", "fy24", "40"),
            _account("opex_including_da", "fy24", "10"),
            _account("depreciation_amortization", "fy24", "5"),
        ],
    )
    cells = _frame(regs)["FY:fy24"]
    gross = cells["gross_profit"]
    assert gross.value == Decimal(40) and gross.stated == Decimal(40)
    for key in ("gross_profit", "ebit", "ebitda", "adjusted_ebitda"):
        assert cells[key].note == "sign normalised", key


def test_income_sums_keep_why_their_components_are_missing() -> None:
    rows = [("revenue", "50"), ("cogs", "-30"), ("opex_including_da", "-5")]
    rows.append(("depreciation_amortization", "-2"))
    regs = _registers(
        GAPPED, [_account(metric, p, value) for p in ("h1", "h2", "fy24") for metric, value in rows]
    )
    cells = _frame(regs)["FY:fy24"]
    for key in ("gross_profit", "ebit", "ebitda", "adjusted_ebitda"):
        cell = cells[key]
        assert cell.value is None, key
        assert cell.reason == "COMPONENT_MISSING", key
        assert cell.note == UNSPANNED, key


def test_a_differing_stated_figure_is_noted_after_the_cell_own_note() -> None:
    regs = _registers(
        FY,
        [
            _account("revenue", "fy24", "100"),
            _account("cogs", "fy24", "60"),
            _account("gross_profit", "fy24", "45"),  # CP-1 stated 45; 100 - 60 is 40
            _account("opex_including_da", "fy24", "-10"),
            _account("depreciation_amortization", "fy24", "-5"),
        ],
    )
    gross = _frame(regs)["FY:fy24"]["gross_profit"]
    assert gross.value == Decimal(40)
    assert gross.stated == Decimal(45)
    assert gross.note == "sign normalised; differs from CP-1 stated"


def test_an_excluded_addback_keeps_why_it_is_missing() -> None:
    accounts = [
        _account(metric, p, value)
        for p in ("h1", "h2")
        for metric, value in (("revenue", "50"), ("ebitda", "10"))
    ]
    addbacks = tuple(
        AddbackRow(
            "synergy",
            "Synergies",
            "SYNERGY",
            "UNREALIZED",
            1,
            p,
            Decimal(3),
            SourceRef("s1", f"synergy@{p}", "3"),
        )
        for p in ("h1", "h2")
    )
    regs = _registers(GAPPED, accounts, addbacks=addbacks)
    cell = _frame(regs, exclude_unrealised=True)["FY:fy24"]["addback:synergy"]
    assert cell.value is None
    assert cell.note == f"{UNSPANNED}; excluded"
    stated = _frame(regs, exclude_unrealised=True)["Q:h2"]["addback:synergy"]
    assert stated.value == Decimal(3) and stated.note == "excluded"


def _facility(facility_id: str, period_id: str, currency: str, carrying: str) -> FacilityRow:
    return FacilityRow(
        facility_id,
        facility_id,
        period_id,
        "TERM LOAN",
        currency,
        Decimal(carrying),
        None,
        None,
        "SECURED",
        "SENIOR",
        "NOT_LEASE",
        "2030-01-01",
        "S+300",
        "FLOATING",
        "SOFR",
        Decimal(300),
        None,
        None,
        None,
        SourceRef("s1", f"{facility_id}@{period_id}", carrying),
    )


def test_debt_non_cash_residual_carries_the_foreign_facility_exclusion() -> None:
    periods = [
        _period("fy23", "FY", "2023-01-01", "2023-12-31", 365),
        _period("fy24", "FY", "2024-01-01", "2024-12-31", 366),
    ]
    facilities = (
        _facility("TLB_EUR", "fy23", "EUR", "300"),
        _facility("TLA", "fy23", "USD", "100"),
        _facility("TLB_EUR", "fy24", "EUR", "400"),
        _facility("TLA", "fy24", "USD", "90"),
    )
    accounts = [_account("net_debt_issue_repay", "fy24", "-10"), _account("revenue", "fy24", "1")]
    cells = _frame(_registers(periods, accounts, facilities))["FY:fy24"]
    foreign = "excludes facility in another currency"
    assert cells["total_debt"].value == Decimal(90)
    assert cells["debt_opening"].value == Decimal(100)
    residual = cells["debt_non_cash"]
    assert residual.value == Decimal(0)
    assert residual.note == f"residual; {foreign}"


def test_debt_non_cash_residual_without_exclusions_stays_plain() -> None:
    periods = [
        _period("fy23", "FY", "2023-01-01", "2023-12-31", 365),
        _period("fy24", "FY", "2024-01-01", "2024-12-31", 366),
    ]
    facilities = (_facility("TLA", "fy23", "USD", "100"), _facility("TLA", "fy24", "USD", "95"))
    accounts = [_account("net_debt_issue_repay", "fy24", "-10"), _account("revenue", "fy24", "1")]
    residual = _frame(_registers(periods, accounts, facilities))["FY:fy24"]["debt_non_cash"]
    assert residual.value == Decimal(5)
    assert residual.note == "residual"
