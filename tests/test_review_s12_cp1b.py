"""Review S12 (CP-1B): fiscal years are read as ASCII digits everywhere, so a register year that
`str.isdigit` accepts but `int` rejects, or a non-ASCII year, offers no default pair instead of
raising out of the view or offering a pair the validator then refuses."""

import pytest

from deploy_vii.contracts import Fact
from deploy_workflow.owners import cp1b


def _row(text: str) -> dict[str, Fact]:
    def fact(field: str, value: str) -> Fact:
        return Fact(
            fact_id=field,
            label=field,
            table_id="T4.14",
            row_id="r",
            field=field,
            text=value,
        )

    return {"fiscal_year": fact("fiscal_year", text), "period_type": fact("period_type", "FY")}


@pytest.mark.parametrize("text", ["²", "２０２５", "٢٠٢٥", "2025²"])
def test_non_ascii_fiscal_year_offers_no_default_pair(text: str) -> None:
    assert cp1b._default_pairs({"fy": _row(text)}) == ()
    assert cp1b._prior_year({"fy": _row(text)}, "fy") is None


def test_ascii_fiscal_year_offers_both_default_pairs() -> None:
    assert cp1b._default_pairs({"fy": _row("2025")}) == (
        ("q3-2025", "q4-2025"),
        ("fy-2024", "fy-2025"),
    )
    assert cp1b._prior_year({"fy": _row("2025")}, "fy") == 2024
