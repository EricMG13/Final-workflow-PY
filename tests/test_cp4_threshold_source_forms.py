"""Source-form regressions from the actual 2033 notes indenture, Section 9.02.

Mixed fractional percentages are outside the Decimal parser's supported forms;
they must never turn into the denominator as a different consent threshold.
These formatting controls do not establish current issuer capacity/compliance.
"""

from decimal import Decimal

import pytest

from deploy_vii.cp4_legal import parse_threshold


@pytest.mark.parametrize(
    "text",
    [
        "at least 66^{2}⁄_{3}%",  # Actual public web-tool rendering.
        "66⅔%",
        "66 2/3%",
        "66 2 / 3 %",
        "66 2⁄3 percent",
        "2/3 per cent",
        "66\n2 /\t3%",
        "66 2 / +3%",
        "66 2 / −3%",
    ],
)
def test_fractional_percent_is_not_its_denominator(text: str) -> None:
    value, reason = parse_threshold(text, "percent")
    assert value is None
    assert reason


@pytest.mark.parametrize(
    ("text", "unit", "expected"),
    [
        ("greater than 2.0 to 1.0", "multiple", Decimal("2.0")),
        ("35.0%", "percent", Decimal("35.0")),
        ("75% of assets/property", "percent", Decimal(75)),
        ("50% on 1/2/2025", "percent", Decimal(50)),
    ],
)
def test_supported_thresholds_keep_their_exact_value(
    text: str, unit: str, expected: Decimal
) -> None:
    assert parse_threshold(text, unit) == (expected, None)
