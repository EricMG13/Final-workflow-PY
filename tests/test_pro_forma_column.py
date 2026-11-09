"""S12-C05: the PF-LTM debt roll-forward shows only the pro forma closing."""

from decimal import Decimal as D

from deploy_vii.model import history
from deploy_vii.model.frame import SourceRef
from deploy_vii.model.registers import (
    AccountRow,
    Cp1Registers,
    FacilityRow,
    PeriodRow,
    PfAdjustmentRow,
)
from deploy_vii.model.statements import pro_forma_column, statement_frame

SRC = SourceRef("s1", "p1", "x")


def _facility(period: str, principal: int) -> FacilityRow:
    return FacilityRow(
        "TL",
        "TL",
        period,
        "TERM_LOAN",
        "USD",
        D(principal),
        None,
        None,
        "SECURED",
        "SENIOR",
        "NOT_LEASE",
        None,
        "x",
        "NOT_STATED",
        "NOT_STATED",
        None,
        None,
        None,
        None,
        SRC,
    )


def test_a_total_debt_adjustment_leaves_a_closing_that_no_blanked_line_contradicts() -> None:
    # By hand: debt 100 at FY24 and 125 at FY25, 20 raised in FY25, so the LTM roll-forward is
    # opening 100, raised 20, non-cash 5, closing 125. A pro forma +50 of total debt gives a PF
    # closing of 175; opening + non-cash would be 105, so the three lines that no longer foot to it
    # are not applicable and total debt and the closing are both 175.
    fy24 = PeriodRow(
        "FY24", "FY2024", None, "FY", "2024-01-01", "2024-12-31", 366, "USD", "MILLIONS", ()
    )
    fy25 = PeriodRow(
        "FY25", "FY2025", None, "FY", "2025-01-01", "2025-12-31", 365, "USD", "MILLIONS", ()
    )
    accounts = (AccountRow("net_debt_issue_repay", "FY25", D(20), "VERIFIED", SRC),)
    refinancing = (PfAdjustmentRow("pf1", "refi", "FY25", "REFINANCING", "total_debt", D(50), SRC),)
    regs = Cp1Registers(
        (fy24, fy25),
        accounts,
        (),
        (),
        (),
        (_facility("FY24", 100), _facility("FY25", 125)),
        refinancing,
        "USD",
        "MILLIONS",
    )
    columns = history.historical_columns(regs)
    frame = statement_frame(history.account_frame(regs, columns), columns, regs)
    ltm = next(c for c in columns if c.period_id == "FY25")
    keys = ("debt_opening", "debt_raised_net", "debt_non_cash", "debt_closing")
    assert [frame[ltm.column_id][k].value for k in keys] == [D(100), D(20), D(5), D(125)]
    result = pro_forma_column(regs, ltm, frame)
    assert result is not None
    column, pro_forma = result
    cells = pro_forma[column.column_id]
    assert [(cells[k].value, cells[k].reason) for k in keys] == [
        (None, "NOT_APPLICABLE"),
        (None, "NOT_APPLICABLE"),
        (None, "NOT_APPLICABLE"),
        (D(175), None),
    ]
    assert cells["total_debt"].value == D(175)
