"""S05 review: a minus sign written against a threshold's number is part of the threshold.
methods/cp4.md: `threshold_value` is the number exactly as the quote writes it, and Python
rejects a stated value that differs from the number it reads."""

from decimal import Decimal

import pytest

from deploy_vii.business_context import Quote
from deploy_vii.cp4_legal import Covenant, _threshold_issues, headroom, parse_threshold


@pytest.mark.parametrize(
    ("text", "unit", "expected"),
    [
        ("shall not be less than -2.5%", "percent", Decimal("-2.5")),
        ("shall not be less than −2.5 per cent", "percent", Decimal("-2.5")),
        ("shall not exceed -0.50x", "multiple", Decimal("-0.50")),
        ("shall not exceed -0.50 to 1.00", "multiple", Decimal("-0.50")),
        # A dash after a digit or letter, or before a space, separates; it is no sign.
        ("between 3.0-4.0x", "multiple", Decimal("4.0")),
        ("Leverage-2.00x", "multiple", Decimal("2.00")),
        ("from 2.5 - 3.0x", "multiple", Decimal("3.0")),
        ("not less than 12.5%", "percent", Decimal("12.5")),
    ],
)
def test_parse_threshold_keeps_a_written_sign(text: str, unit: str, expected: Decimal) -> None:
    value, reason = parse_threshold(text, unit)
    assert reason is None
    assert value == expected
    assert str(value) == str(expected)


def _floor(stated: str) -> Covenant:
    text = "shall not be less than -2.5%"
    return Covenant(
        name="Minimum margin",
        kind="maintenance",
        document_id="S1",
        clause="7.1",
        definition_text="Margin",
        test_formula="Margin",
        threshold_text=text,
        threshold_unit="percent",
        threshold_value=stated,
        comparison=">=",
        metric_ref=None,
        metric_basis="Same definition",
        facility_ids=(),
        period_scope="Each quarter",
        citations=(Quote(source_id="S1", locator="p. 4", quote=f"The margin {text}."),),
        limitation=None,
    )


def test_the_signed_stated_value_is_accepted_and_the_unsigned_refused() -> None:
    assert _threshold_issues("covenants[0]", _floor("-2.5")) == []
    assert _threshold_issues("covenants[0]", _floor("2.5")) == [
        "covenants[0]: threshold_value 2.5 differs from -2.5"
    ]


def test_headroom_against_a_negative_floor() -> None:
    # Metric -1.0% (CP-1 decimal fraction -0.010) against a floor of -2.5%: 1.5 pp within.
    value, _ = parse_threshold("shall not be less than -2.5%", "percent")
    assert value is not None
    room = headroom(value / 100, ">=", Decimal("-0.010"))
    assert room.within is True
    assert room.amount * 100 == Decimal("1.5")
