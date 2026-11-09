"""`states_trailing_period`: the period CP-1 states on a quarter column's trailing ratio.

Expectations are hand-counted days to 2025-12-31: from 2025-01-01 365 days, 2025-01-02 364,
2024-12-26 371 (6 days of 2024 + 365), 2024-12-25 372, 2025-01-03 363, 2024-12-24 373.
"""

import pytest

from deploy_workflow.trailing_period import states_trailing_period as stated


@pytest.mark.parametrize(
    ("period", "end", "label"),
    [
        ("LTM Q4 25: 2025-01-01 to 2025-12-31", "2025-12-31", None),
        ("LTM Q4 25: 2025-01-01 to 2025-12-31", "2025-12-31", "Q4 25"),
        ("LTM Q3 25: null to 2025-09-30", "2025-09-30", "Q3 25"),
        ("LTM Q4 25: 2025-01-02 to 2025-12-31", "2025-12-31", None),  # 364 days
        ("LTM Q4 25: 2024-12-26 to 2025-12-31", "2025-12-31", None),  # 371 days
    ],
)
def test_accepted(period: str, end: str, label: str | None) -> None:
    assert stated(period, end, label)


@pytest.mark.parametrize(
    ("period", "end", "label"),
    [
        (None, "2025-12-31", None),
        ("", "2025-12-31", None),
        ("Q4 25: 2025-01-01 to 2025-12-31", "2025-12-31", None),  # not labelled trailing
        ("LTM Q4 25: 2025-01-01 to 2025-12-31", "2025-12-30", None),  # another end
        ("LTM Q4 25: 2025-01-01 to 2025-12-31", "2025-12-31", "Q3 25"),  # another quarter
        ("LTM Q4 25: 2025-01-03 to 2025-12-31", "2025-12-31", None),  # 363 days
        ("LTM Q4 25: 2024-12-25 to 2025-12-31", "2025-12-31", None),  # 372 days
        ("LTM Q4 25: 2024-12-24 to 2025-12-31", "2025-12-31", None),  # 373 days
        ("LTM Q4 25: 2025-12-31 to 2025-12-31", "2025-12-31", None),  # one day
        ("LTM Q4 25: 2026-01-01 to 2025-12-31", "2025-12-31", None),  # starts after the end
        ("LTM Q4 25: 2025-02-30 to 2025-12-31", "2025-12-31", None),  # not a date
        ("LTM Q4 25: Null to 2025-12-31", "2025-12-31", None),
        ("LTM Q4 25: 2025-01-01 to 2025-12-31 and more", "2025-12-31", None),
        ("xLTM Q4 25: null to 2025-12-31", "2025-12-31", None),
    ],
)
def test_refused(period: str | None, end: str, label: str | None) -> None:
    assert not stated(period, end, label)
