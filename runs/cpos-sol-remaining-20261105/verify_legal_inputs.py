"""Read-only legal-source controls; hypothetical boundaries are not issuer capacity."""

import hashlib
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from deploy_vii.cp4_legal import headroom, parse_threshold


def check():
    root = Path(__file__).resolve().parents[2]
    raw = (root / "runs/tdg-004/legal-source/source-lines.txt").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "cb2c0c77e7ec1f90e5a7117a5df7e16cd2556b02e7be7ca43fbf4d64ed585b05"
    )
    lines = raw.decode().splitlines()
    assert len(lines) == 2877
    assert all(line.startswith(f"L{i}:") for i, line in enumerate(lines))
    for index, unit, expected in [
        (1295, "multiple", "2.0"),
        (1265, "multiple", "2.0"),
        (409, "percent", "35.0"),
    ]:
        assert parse_threshold(lines[index], unit) == (Decimal(expected), None)
    assert "66^{2}⁄_{3}%" in lines[1860]
    for text in [lines[1860], "66⅔%", "66 2/3%", "66 2 / 3 %"]:
        value, reason = parse_threshold(text, "percent")
        assert value is None and reason
    boundary = []
    with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
        for metric, expected, within in [
            ("1.99", "-0.01", False),
            ("2.00", "0.00", False),
            ("2.01", "0.01", True),
        ]:
            out = headroom(Decimal(2), ">", Decimal(metric))
            assert Fraction(out.amount) == Fraction(expected)
            assert Fraction(out.share) == Fraction(expected) / 2
            assert out.within is within
            boundary.append(
                {
                    "synthetic_metric": metric,
                    "headroom_x": str(out.amount),
                    "within_strict_test": within,
                }
            )
    assert "$1,500,000,000" in lines[915]
    assert "101%" in lines[1345]
    assert "[•], 2033" in lines[2650]
    conditional = Fraction(1500) * Fraction(101, 100)
    assert conditional == 1515
    rows = [
        ["incurrence_threshold_x", "2"],
        ["restricted_payment_threshold_x", "2"],
        ["clause_M_post_adjustment_cap_percent", "35"],
        ["original_notes_principal_USDm", "1500"],
        ["conditional_all_original_principal_101_percent_USDm", "1515"],
        ["conditional_premium_component_USDm", "15"],
        ["actual_current_legal_FCCR", "—"],
        ["actual_unused_ratio_debt_capacity_USDm", "—"],
        ["conditional_accrued_interest_USDm", "—"],
    ]
    return (
        {
            "scope": "Read-only source/parser checks and synthetic strict-boundary controls; no actual issuer headroom. Conditional 101% assumes all original principal tendered, no current-outstanding or actual-trigger assertion.",
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "source_threshold_checks": 3,
            "fraction_refusals": 4,
            "strict_boundary_controls": boundary,
            "conditional_principal_component_USDm": "1515",
            "conditional_interest_USDm": None,
        },
        {"heading": "Legal numeric controls", "columns": ["Metric", "Value"], "rows": rows},
    )


def check_arcc():
    """Published asset-coverage cushion, not dollar borrowing permission."""
    import re

    base = Path(__file__).resolve().parents[2] / "runs/arcc-2024-001/sources"
    annual = (base / "annual-pages.txt").read_bytes()
    assert hashlib.sha256(annual).hexdigest() == (
        "9e216fdd000f529b4f1c452d5786b2ec9e0cab69e8fcd9659558d87d8b4e1976"
    )
    pages = dict(
        re.findall(r"=== PDF PAGE (\d+) ===\n(.*?)(?==== PDF PAGE |\Z)", annual.decode(), re.DOTALL)
    )
    assert "July 2029 Notes\nFiscal 2024 $ 850 $ 1,962" in pages["65"]
    assert "multiplied by $1,000" in pages["65"]
    assert "150% after such borrowing" in pages["274"]
    assert "$6,732" in pages["275"] and "$4,513" in pages["275"]
    for name, sha, length in [
        ("base", "ef8ad4d8a3d5902746726697b6f6fa53058d7445b59d99157cbea6258bf2d459", 1706),
        ("supplement", "bf82a65cae422d4814fa292ab3b9e5e5324f74d09643d6367ad6110055e6390c", 525),
    ]:
        raw = (base / (name + "-lines.txt")).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == sha
        assert len(raw.decode().splitlines()) == length
    expected = Fraction(1962, 1000) - Fraction(150, 100)
    assert expected == Fraction(462, 1000)
    assert Fraction(6732) - Fraction(4513) == 2219
    with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
        out = headroom(Decimal("1.5"), ">=", Decimal("1.962"))
        assert Fraction(out.amount) == expected and out.within
        assert Fraction(out.share) == Fraction(308, 1000)
        for metric, room, within in [
            ("1.499", "-0.001", False),
            ("1.500", "0", True),
            ("1.501", "0.001", True),
        ]:
            out = headroom(Decimal("1.5"), ">=", Decimal(metric))
            assert Fraction(out.amount) == Fraction(room) and out.within == within
    rows = [
        ["published_coverage_ratio", "1.962"],
        ["reported_minimum_ratio", "1.5"],
        ["published_coverage_cushion_ratio", "0.462"],
        ["published_coverage_cushion_pp", "46.2"],
        ["whole_percent_presentation_cushion_pp", "46"],
        ["conditional_facility_ceiling_difference_USDm", "2219"],
        ["actual_usable_dollar_debt_capacity_USDm", "—"],
        ["actual_RP_capacity_USDm", "—"],
        ["actual_leakage_capacity_USDm", "—"],
    ]
    return (
        {
            "scope": "Unchanged pure headroom helper versus independently frozen source-derived Fraction expectations. Published precision, not unrounded certificate or usable dollar capacity. Three synthetic inclusive-boundary cases, not issuer events.",
            "published_ratio": "1.962",
            "threshold": "1.5",
            "cushion_ratio": "0.462",
            "cushion_pp": "46.2",
            "conditional_commitment_ceiling_difference_USDm": "2219",
            "actual_usable_capacity_USDm": None,
        },
        {"heading": "Capacity controls", "columns": ["Metric", "Value"], "rows": rows},
    )


if __name__ == "__main__":
    import json

    print(json.dumps(check()[0], indent=2))
