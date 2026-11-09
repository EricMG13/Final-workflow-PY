"""A line the host recomputes where CP-1 states its own figure (gross profit,
EBIT, EBITDA, adjusted EBITDA) keeps the notes its sum carries when CP-1's
figure is attached: sign normalised, why a part is missing, components that do
not span the period; "differs from CP-1 stated" is added after them, never in
their place (review of S12-vii-financial-engine-C03)."""

from decimal import Decimal

from deploy_vii.model import history
from deploy_vii.model._cells import DIFFERS, SIGN_NORMALISED, UNSPANNED
from deploy_vii.model.frame import Cell, SourceRef
from deploy_vii.model.registers import AccountRow, Cp1Registers, PeriodRow
from deploy_vii.model.statements import statement_frame

SOURCE = SourceRef("s1", "p1", "x")
FY = PeriodRow("FY25", "FY2025", None, "FY", "2025-01-01", "2025-12-31", 365, "USD", "MILLIONS", ())


def _row(metric: str, period: str, value: str | None) -> AccountRow:
    amount = None if value is None else Decimal(value)
    return AccountRow(metric, period, amount, "VERIFIED", SOURCE)


def _frame(
    periods: tuple[PeriodRow, ...], rows: tuple[AccountRow, ...]
) -> dict[str, dict[str, Cell]]:
    regs = Cp1Registers(periods, rows, (), (), (), (), (), "USD", "MILLIONS")
    columns = history.historical_columns(regs)
    frame = statement_frame(history.account_frame(regs, columns), columns, regs)
    return {column.column_id: frame[column.column_id] for column in columns}


def test_sign_normalised_cogs_keeps_its_note_on_every_recomputed_line() -> None:
    # Hand-derived: cogs written +60 reads -60 (sign normalised); gross profit
    # 100 - 60 = 40 equals CP-1's 40; EBIT 40 - 20 = 20; EBITDA 20 - (-5) = 25.
    rows = (
        _row("revenue", "FY25", "100"),
        _row("cogs", "FY25", "60"),
        _row("gross_profit", "FY25", "40"),
        _row("opex_including_da", "FY25", "-20"),
        _row("depreciation_amortization", "FY25", "-5"),
    )
    cells = _frame((FY,), rows)["FY:FY25"]
    expected = {"gross_profit": "40", "ebit": "20", "ebitda": "25"}
    for line, value in expected.items():
        assert cells[line].value == Decimal(value), line
        assert cells[line].note == SIGN_NORMALISED, line
    assert cells["gross_profit"].stated == Decimal(40)


def test_differs_is_added_after_the_sign_normalised_note() -> None:
    # Hand-derived: gross profit 100 - 60 = 40; CP-1 states 45, which is more
    # than half a unit (0.5) away, so both notes stay, in that order.
    rows = (
        _row("revenue", "FY25", "100"),
        _row("cogs", "FY25", "60"),
        _row("gross_profit", "FY25", "45"),
    )
    cells = _frame((FY,), rows)["FY:FY25"]
    gross = cells["gross_profit"]
    assert gross.value == Decimal(40)
    assert gross.stated == Decimal(45)
    assert gross.note == f"{SIGN_NORMALISED}; {DIFFERS}"


def test_a_line_without_any_note_stays_unnoted() -> None:
    # Hand-derived: cogs written -60 needs no sign normalisation; 100 - 60 = 40
    # equals CP-1's 40, so gross profit has no note at all.
    rows = (
        _row("revenue", "FY25", "100"),
        _row("cogs", "FY25", "-60"),
        _row("gross_profit", "FY25", "40"),
    )
    cells = _frame((FY,), rows)["FY:FY25"]
    assert cells["gross_profit"].value == Decimal(40)
    assert cells["gross_profit"].note is None


def test_unspanned_components_keep_why_gross_profit_is_missing() -> None:
    # A FY naming only Q1 as its components does not span the year: revenue
    # is COMPONENT_MISSING noted UNSPANNED, and so is gross profit built from it.
    q1 = PeriodRow(
        "Q1", "FY2025", "1", "QUARTER", "2025-01-01", "2025-03-31", 90, "USD", "MILLIONS", ()
    )
    fy = PeriodRow(
        "FY25", "FY2025", None, "FY", "2025-01-01", "2025-12-31", 365, "USD", "MILLIONS", ("Q1",)
    )
    rows = (_row("revenue", "Q1", "10"), _row("cogs", "Q1", "-6"))
    frames = _frame((q1, fy), rows)
    derived = [cells for column_id, cells in frames.items() if not column_id.startswith("Q:")]
    assert derived  # the FY and LTM columns
    for cells in derived:
        assert cells["gross_profit"].reason == "COMPONENT_MISSING"
        assert cells["gross_profit"].note == UNSPANNED
        assert cells["ebit"].note == UNSPANNED


def test_sign_normalised_reaches_adjusted_ebitda_and_differs_stays_on_its_line() -> None:
    # Hand-derived: gross profit 100 - 60 = 40 against CP-1's 45 -> noted both;
    # EBIT 40 - 20 = 20 and EBITDA 20 + 5 = 25 equal CP-1's, so they carry only
    # "sign normalised", and adjusted EBITDA (25, no add-backs) inherits it from EBITDA.
    rows = (
        _row("revenue", "FY25", "100"),
        _row("cogs", "FY25", "60"),
        _row("gross_profit", "FY25", "45"),
        _row("opex_including_da", "FY25", "-20"),
        _row("depreciation_amortization", "FY25", "-5"),
        _row("ebit", "FY25", "20"),
        _row("ebitda", "FY25", "25"),
        _row("adjusted_ebitda", "FY25", "25"),
    )
    cells = _frame((FY,), rows)["FY:FY25"]
    assert cells["gross_profit"].note == f"{SIGN_NORMALISED}; {DIFFERS}"
    for line in ("ebit", "ebitda", "adjusted_ebitda"):
        assert cells[line].note == SIGN_NORMALISED, line
    assert cells["adjusted_ebitda"].value == Decimal(25)
