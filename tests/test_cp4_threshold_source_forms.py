"""Source-form regressions from the actual 2033 notes indenture, Section 9.02.

Mixed fractional percentages are outside the Decimal parser's supported forms;
they must never turn into the denominator as a different consent threshold.
These formatting controls do not establish current issuer capacity/compliance.
"""

from decimal import Decimal

import pytest

from deploy_vii.cp4_legal import Covenant, Quote, _threshold_issues, parse_threshold


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


def _covenant(threshold_text: str, threshold_value: str, quote: str) -> Covenant:
    return Covenant(
        name="Total Net Leverage Ratio",
        kind="maintenance",
        document_id="credit-agreement",
        clause="Section 7.11",
        definition_text="Consolidated Total Net Debt to Consolidated EBITDA",
        test_formula="total net debt / EBITDA",
        threshold_text=threshold_text,
        threshold_unit="multiple",
        threshold_value=threshold_value,
        comparison="<=",
        metric_ref=None,
        metric_basis="Not determinable",
        facility_ids=(),
        period_scope="each fiscal quarter",
        citations=(Quote(source_id="credit-agreement", locator="page 88", quote=quote),),
        limitation=None,
    )


COVENANT_QUOTE = "the Total Net Leverage Ratio shall not exceed 12.50:1.00 as of the last day"


def test_threshold_cut_out_of_a_larger_figure_is_not_quoted() -> None:
    """S13 A03/C05: `2.50:1.00` is a substring of `12.50:1.00` but not a quote of it, so the
    12.50x covenant cannot be recorded as 2.50x. The whole threshold is accepted without issue.
    No pack sources are passed: the S09 sentence check then reads the quote alone."""
    issues = _threshold_issues("covenants[0]", _covenant("2.50:1.00", "2.50", COVENANT_QUOTE), ())
    assert issues == ["covenants[0]: threshold_text is not part of the row's quotes"]
    assert (
        _threshold_issues("covenants[0]", _covenant("12.50:1.00", "12.50", COVENANT_QUOTE), ())
        == []
    )
