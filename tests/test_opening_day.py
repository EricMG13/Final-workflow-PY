"""S12-C08: one opening-balance day rule and one statement unit factor table."""

from datetime import date
from decimal import Decimal

from deploy_vii import statement_output
from deploy_vii.financial_contracts import STATEMENT_UNIT_FACTORS, opening_day


def test_opening_day_is_the_day_before_the_start() -> None:
    # By hand: a period starting 2025-01-01 opens on 2024-12-31 and one starting 2024-03-01 on
    # 2024-02-29 (leap year); a missing start, or 0001-01-01 (no earlier day), has none.
    assert opening_day(date(2025, 1, 1)) == date(2024, 12, 31)
    assert opening_day(date(2024, 3, 1)) == date(2024, 2, 29)
    assert opening_day(None) is None
    assert opening_day(date(1, 1, 1)) is None


def test_statement_output_reads_the_contract_unit_factors() -> None:
    assert not hasattr(statement_output, "_SCALE_FACTORS")
    assert STATEMENT_UNIT_FACTORS == {
        "UNITS": Decimal(1),
        "THOUSANDS": Decimal(1000),
        "MILLIONS": Decimal(1000000),
    }
