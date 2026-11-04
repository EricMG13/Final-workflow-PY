"""A bounded operating-expense bridge from retained statement observations.

The two expense lines must share a source statement and reconcile exactly to
reported gross profit and EBIT. No residual becomes an invented expense.
"""

from decimal import localcontext
import re

from deploy_vii.financial_contracts import FinancialBook, StatementLine, statement_dimensions
from deploy_vii.model._cells import CONTEXT, calc
from deploy_vii.model.frame import Cell, SourceRef


def opex_composition(book: FinancialBook, period_id: str) -> Cell | None:
    labels = {
        "SELLING AND ADMINISTRATIVE EXPENSES": "sga",
        "AMORTIZATION OF INTANGIBLE ASSETS": "amortization",
        "GROSS PROFIT": "gross_profit",
        "INCOME FROM OPERATIONS": "ebit",
    }
    selected: dict[str, StatementLine] = {}
    for row in book.statement_lines:
        if row.statement != "IS" or row.period_id != period_id:
            continue
        key = labels.get(re.sub(r"\s+", " ", row.label.strip().upper()))
        if key is None:
            continue
        dimensions = statement_dimensions(book, row)
        if key in selected or row.value.amount is None or dimensions.kind != "monetary":
            return None
        if dimensions.currency != book.currency or dimensions.scale != book.unit:
            return None
        selected[key] = row
    if set(selected) != set(labels.values()):
        return None
    # Every component must be on the same cited statement (source hash and page/table).
    locations = [
        {(c.source_id, c.source_sha256, c.locator) for c in row.value.citations}
        for row in selected.values()
    ]
    if not set.intersection(*locations):
        return None
    cells = {}
    for key, row in selected.items():
        value = row.value.amount
        assert value is not None
        if key in {"sga", "amortization"} and value < 0:
            return None
        cells[key] = Cell(value, basis="REPORTED", sources=(
            SourceRef(row.value.observation_id, "financial-observation", str(value)),
        ))
    with localcontext(CONTEXT):
        expense = calc(((cells["sga"], -1), (cells["amortization"], -1)),
                       "SG&A plus intangible amortization")
        reconciled = calc(((cells["gross_profit"], 1), (expense, 1), (cells["ebit"], -1)))
    return expense if reconciled.value == 0 else None
