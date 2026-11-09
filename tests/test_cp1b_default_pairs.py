"""S05-C06: cp1b._default_pairs reads ASCII fiscal years only and never raises."""

from types import SimpleNamespace

import pytest

from deploy_workflow.owners import cp1b


def _rows(*years: str) -> dict[str, dict[str, SimpleNamespace]]:
    return {f"r{i}": {"fiscal_year": SimpleNamespace(text=y)} for i, y in enumerate(years)}


def test_ascii_years_give_the_q3_q4_pair_and_the_fy_pair() -> None:
    # Hand-derived: 2025 -> (q3-2025, q4-2025) and (fy-2024, fy-2025); "02025" is the same year.
    got = cp1b._default_pairs(_rows("2025", "02025"))  # type: ignore[arg-type]
    assert got == (("q3-2025", "q4-2025"), ("fy-2024", "fy-2025"))


@pytest.mark.parametrize("year", ["2025²", "2025₂", "٢٠٢٥", "２０２５", "", "FY2025", "2025.0"])
def test_a_non_ascii_or_non_digit_year_offers_no_pair_instead_of_raising(year: str) -> None:
    assert cp1b._default_pairs(_rows(year)) == ()  # type: ignore[arg-type]
    assert cp1b._default_pairs(_rows(year, "2026")) == (  # type: ignore[arg-type]
        ("q3-2026", "q4-2026"),
        ("fy-2025", "fy-2026"),
    )
