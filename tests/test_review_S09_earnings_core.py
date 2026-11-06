"""S09 review regressions for the paired-period delta core (`deploy_workflow.earnings`).

Growth over a negative base is not meaningful (its sign would invert), as CP-2D/CP-3C treat a
zero or negative denominator; an absent prior is a comparative gap only when its id names a
period of the current kind. Expected values are literals.
"""

from decimal import Decimal

import pytest
from test_earnings import build, change, fixture, point, refusal


@pytest.mark.parametrize(
    ("prior", "current", "delta"),
    [
        (Decimal(-10), Decimal(-5), Decimal(5)),  # improvement: was -50%
        (Decimal(-10), Decimal(5), Decimal(15)),  # turn to positive: was -150%
        (Decimal(-10), Decimal(-20), Decimal(-10)),  # deterioration: was +100%
    ],
)
def test_growth_over_a_negative_base_is_missing_with_its_reason(prior, current, delta):
    module = change(fixture(), "value.ebitda.q3-2025", amount=prior)
    module = change(module, "value.ebitda.q4-2025", amount=current)
    p = point(build(module), "ebitda")
    assert (p.prior_value, p.current_value) == (prior, current)
    assert p.delta == delta and p.delta_status == "known"
    assert p.growth is None and p.growth_status == "missing"
    assert p.reason == "ZERO_OR_NEGATIVE_DENOMINATOR"


def test_growth_over_a_zero_base_keeps_its_pinned_code():
    module = change(fixture(), "value.revenue.q3-2025", amount=Decimal(0))
    p = point(build(module), "revenue")
    assert p.growth is None and p.growth_status == "missing" and p.reason == "ZERO_DENOMINATOR"


def test_growth_over_a_positive_base_is_unchanged():
    module = change(fixture(), "value.revenue.q3-2025", amount=Decimal(40))
    module = change(module, "value.revenue.q4-2025", amount=Decimal(50))
    p = point(build(module), "revenue")
    assert p.growth == Decimal("0.25") and p.growth_status == "known" and p.reason is None


@pytest.mark.parametrize(
    ("prior", "current"),
    [("fy-2024", "q4-2025"), ("q4-2024", "fy-2025"), ("q3-2024", "fy-2025")],
)
def test_an_absent_prior_of_another_kind_is_incompatible_not_a_gap(prior, current):
    refusal(fixture(), "incompatible_periods", prior, current)


@pytest.mark.parametrize(
    ("prior", "current"),
    [("fy-2024", "fy-2025"), ("q4-2024", "q4-2025"), ("q2-2025", "q4-2025")],
)
def test_an_absent_prior_of_the_current_kind_stays_a_comparative_gap(prior, current):
    report = build(prior=prior, current=current)
    assert report.prior_basis_id is None
    assert all("COMPARATIVE_NOT_SUPPLIED" in p.reason for p in report.points)
