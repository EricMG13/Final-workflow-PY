"""Historical pair fixture: unchanged float helper versus independent Decimal PV."""

import hashlib
import importlib.util
import json
import sys
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from verify_market_inputs import check as market_check

ROOT = Path(__file__).resolve().parents[2]


def check():
    market, _ = market_check()
    source = ROOT / "runs/arcc-selection-2024-001/sources/March2029-lines.txt"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == (
        "afa48e16a39d3cab0e427ec9bc2967980570f2117223203482d0cf1d84f8bbd3"
    )
    lines = source.read_text().splitlines()
    for index, words in [
        (22, ["US04010LBF94", "Senior Securities"]),
        (23, ["$1,000,000,000"]),
        (24, ["March 1, 2029"]),
        (25, ["5.875%", "commencing September 1, 2024", "twelve 30-day months"]),
        (31, ["February 1, 2029"]),
        (32, ["35 basis points"]),
    ]:
        assert all(word in lines[index] for word in words), index
    frozen = json.loads((source.parents[1] / "expectations.json").read_bytes())
    helper = (
        ROOT
        / "docs/reuse/selected-methods/skills/cp-3d-market-implied-risk/scripts/bond_analytics.py"
    )
    assert hashlib.sha256(helper.read_bytes()).hexdigest() == frozen["helper_sha256"]
    spec = importlib.util.spec_from_file_location("selected_bond_pair", helper)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    rows, outputs, comparisons = [], [], []
    results = {}
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):

        def dec(x):
            f = Fraction(x)
            return Decimal(f.numerator) / Decimal(f.denominator)

        def fmt(x):
            return str((x if isinstance(x, Decimal) else dec(x)).quantize(Decimal(".000001")))

        def days360(d):
            return 360 * (d.year - 2024) + 30 * (d.month - 12) + min(d.day, 30) - 30

        for name, item in frozen["securities"].items():
            march = name == "March2029"
            primary = next(r for r in market["curve"] if r["maturity"] == item["maturity"])
            assert primary["principal_usdm"] == item["principal_usdm"]
            assert primary["estimated_fair_value_usdm"] == item["fair_usdm"]
            assert Fraction(primary["fixed_coupon_pct"]) == Fraction(item["coupon_pct"])
            coupon = Fraction(47, 8) if march else Fraction(119, 20)
            dates = (
                [date(y, m, 1) for y in range(2025, 2030) for m in (3, 9) if (y, m) <= (2029, 3)]
                if march
                else [date(y, m, 15) for y in range(2025, 2030) for m in (1, 7)]
            )
            flows = [
                (Fraction(days360(d), 360), coupon / 2 + (100 if d == dates[-1] else 0))
                for d in dates
            ]
            call_date = date(2029, 2, 1) if march else date(2029, 6, 15)
            call = flows[:-1] + [
                (Fraction(days360(call_date), 360), 100 + coupon * Fraction(150, 360))
            ]
            assert flows == [
                (Fraction(r["t"]), Fraction(r["amount"])) for r in item["maturity_flows"]
            ]
            assert call == [(Fraction(r["t"]), Fraction(r["amount"])) for r in item["call_flows"]]
            accrued = coupon * Fraction(119 if march else 165, 360)
            assert accrued == Fraction(item["accrued"])
            equivalent = Fraction(item["fair_usdm"] * 100, item["principal_usdm"])
            horizon = Fraction((dates[-1] - date(2024, 12, 31)).days, 365)
            benchmark = Fraction(".0427") + (horizon - 3) / 2 * Fraction(".0011")
            assert abs(
                dec(benchmark) * 100 - Decimal(item["benchmark_interpolated_pct"])
            ) < Decimal("1e-43")
            floatflows = [(float(t), float(cf)) for t, cf in flows]
            floatcalls = [(float(t), float(cf)) for t, cf in call]

            def pv(y, flows=flows):
                return sum(dec(cf) * (1 + y / 2) ** (-2 * dec(t)) for t, cf in flows)

            for case, expected in item["cases"].items():
                dirty = equivalent + accrued if case == "assume_clean" else equivalent
                y, cy = (
                    module.yield_to(float(dirty), floatflows),
                    module.yield_to(float(dirty), floatcalls),
                )
                ey, ec = (
                    Decimal(expected["maturity_yield_decimal_expected"]),
                    Decimal(expected["par_call_yield_decimal_expected"]),
                )
                assert abs(pv(ey) - dec(dirty)) < Decimal("1e-37")
                assert abs(pv(ec, call) - dec(dirty)) < Decimal("1e-37")
                assert abs(Decimal(str(y)) - ey) < Decimal("1e-9")
                assert abs(Decimal(str(cy)) - ec) < Decimal("1e-9")
                duration = sum(
                    dec(cf) * dec(t) * (1 + ey / 2) ** (-2 * dec(t) - 1) for t, cf in flows
                ) / dec(dirty)
                assert abs(
                    duration - Decimal(expected["modified_duration_maturity_years"])
                ) < Decimal("1e-40")
                bounds = list(map(Decimal, expected["rounding_maturity_yield_bounds_pct"]))
                actual_bounds = []
                for change, root in zip([Fraction(1, 2), Fraction(-1, 2)], bounds, strict=True):
                    price = dirty + change * 100 / item["principal_usdm"]
                    assert abs(pv(root / 100) - dec(price)) < Decimal("1e-37")
                    value = module.yield_to(float(price), floatflows)
                    assert abs(Decimal(str(value)) * 100 - root) < Decimal("1e-7")
                    actual_bounds.append(value * 100)
                results[name, case] = ey, (ey - dec(benchmark)) * 10000, bounds
                rows.append(
                    [
                        name + "_" + case,
                        *map(
                            fmt,
                            [
                                equivalent,
                                accrued,
                                dirty,
                                ey,
                                ec,
                                min(ey, ec),
                                (ey - dec(benchmark)) * 10000,
                                duration,
                                *bounds,
                            ],
                        ),
                    ]
                )
                outputs.append(
                    {
                        "security": name,
                        "case": case,
                        "isin": item["isin"],
                        "equivalent_exact": str(equivalent),
                        "accrued_exact": str(accrued),
                        "dirty_exact": str(dirty),
                        "maturity_flows": item["maturity_flows"],
                        "par_call_flows": item["call_flows"],
                        "maturity_yield": y,
                        "par_call_yield": cy,
                        "simple_residual_bps": (y - float(benchmark)) * 10000,
                        "modified_duration": sum(
                            cf * t * (1 + y / 2) ** (-2 * t - 1) for t, cf in floatflows
                        )
                        / float(dirty),
                        "rounding_maturity_yield_bounds_pct": actual_bounds,
                    }
                )
        for case in ["assume_clean", "assume_dirty"]:
            jy, js, jb = results["July2029", case]
            my, ms, mb = results["March2029", case]
            comparisons.append(
                [
                    case,
                    *map(
                        fmt,
                        [(jy - my) * 10000, js - ms, (jb[0] - mb[1]) * 100, (jb[1] - mb[0]) * 100],
                    ),
                ]
            )
    return {
        "scope": "Fresh unchanged yield/PV primitives; source-pinned analyst30E/360 dates and conditional evaluated bases, not general dated engine or executable quotes.",
        "cases": outputs,
    }, [
        {
            "heading": "Pair pricing controls",
            "columns": [
                "Security_case",
                "Equivalent",
                "Accrued",
                "Dirty",
                "Maturity_yield_fraction",
                "Par_call_yield_fraction",
                "Minimum_two_legs_fraction",
                "Simple_residual_bps",
                "Modified_duration",
                "Rounding_yield_low_pct",
                "Rounding_yield_high_pct",
            ],
            "rows": rows,
        },
        {
            "heading": "Pair difference controls",
            "columns": [
                "Case",
                "July_minus_March_yield_bps",
                "July_minus_March_residual_bps",
                "Rounding_yield_gap_low_bps",
                "Rounding_yield_gap_high_bps",
            ],
            "rows": comparisons,
        },
    ]
