"""Read-only ARCC pricing fixture; Decimal PV verifies unchanged float primitives."""

import csv
import hashlib
import importlib.util
import io
import json
import re
import sys
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check():
    base = ROOT / "runs/arcc-market-2024-001"
    frozen = json.loads((base / "CP-3D-calculations.json").read_bytes())
    review = json.loads((base / "verification.json").read_bytes())
    annual = (ROOT / "runs/arcc-2024-001/sources/annual-pages.txt").read_bytes()
    assert (
        hashlib.sha256(annual).hexdigest()
        == "9e216fdd000f529b4f1c452d5786b2ec9e0cab69e8fcd9659558d87d8b4e1976"
    )
    pages = dict(
        re.findall(r"=== PDF PAGE (\d+) ===\n(.*?)(?==== PDF PAGE |\Z)", annual.decode(), re.DOTALL)
    )
    normalized = " ".join(pages["291"].split())
    rows = []
    for datum, primary in zip(
        frozen["raw_source_curve"], review["ordered_source_row_checks"], strict=True
    ):
        assert datum["series"] == primary["series"]
        block = primary["exact_source_block"].strip()
        assert block in normalized
        values = [
            None if s == "—" else int(s.replace(",", ""))
            for s in primary["ordered_current_carrying_fair_prior_carrying_fair"]
        ]
        assert (
            values[0] == datum["carrying_usdm"] and values[1] == datum["estimated_fair_value_usdm"]
        )
        assert values[3] == datum["prior_fair_usdm"]
        assert primary["principal_exact"] == datum["principal_usdm"]
        maturity = date.fromisoformat(datum["maturity"])
        title = f"{maturity:%B %Y} Notes"
        terms = re.search(re.escape(title) + r"(?:\(1\))? \$ ([\d,]+) ([\d.]+)%", pages["94"])
        assert terms and int(terms[1].replace(",", "")) == datum["principal_usdm"]
        swap = re.search("Interest rate swap " + re.escape(title) + r" ([\d.]+) %", pages["94"])
        assert Fraction(swap[1] if swap else terms[2]) == Fraction(datum["fixed_coupon_pct"])
        assert f"{maturity:%B} {maturity.day}, {maturity.year}" in pages["94"]
        assert datum["fixed_coupon_pct"] in pages["94"]
        equivalent = Fraction(datum["estimated_fair_value_usdm"] * 100, datum["principal_usdm"])
        assert equivalent == Fraction(datum["evaluated_equivalent_per_100"])
        assert 100 - equivalent == Fraction(datum["discount_to_par_points"])
        prior = (
            None
            if datum["prior_fair_usdm"] is None
            else Fraction(datum["prior_fair_usdm"] * 100, datum["principal_usdm"])
        )
        if prior is None:
            assert (
                datum["prior_equivalent_per_100"] is None
                and datum["change_points_not_total_return"] is None
            )
        else:
            assert prior == Fraction(datum["prior_equivalent_per_100"])
            assert equivalent - prior == Fraction(datum["change_points_not_total_return"])
        rows.append(
            [
                datum["series"],
                str(datum["principal_usdm"]),
                str(datum["carrying_usdm"]),
                str(datum["estimated_fair_value_usdm"]),
                equivalent,
                prior,
                None if prior is None else equivalent - prior,
            ]
        )
    legal = (ROOT / "runs/arcc-2024-001/sources/supplement-lines.txt").read_bytes()
    assert (
        hashlib.sha256(legal).hexdigest()
        == "bf82a65cae422d4814fa292ab3b9e5e5324f74d09643d6367ad6110055e6390c"
    )
    lines = legal.decode().splitlines()
    for idx, words in [
        (73, ["US04010LBG77"]),
        (80, ["5.950%"]),
        (81, ["commencing July"]),
        (83, ["360-day"]),
        (101, ["June"]),
        (102, ["30 basis points"]),
        (111, ["100%"]),
    ]:
        assert all(w in lines[idx] for w in words)
    csvraw = (base / "sources/treasury-2024.csv").read_bytes()
    assert (
        hashlib.sha256(csvraw).hexdigest()
        == "6775840b76cd7fd41121f61d6f6c60184eca6b2ba49954ec7372c463cbeef34d"
    )
    treasury = [
        r for r in csv.DictReader(io.StringIO(csvraw.decode())) if r["Date"] == "12/31/2024"
    ]
    assert len(treasury) == 1 and treasury[0]["3 Yr"] == "4.27" and treasury[0]["5 Yr"] == "4.38"
    horizon = Fraction((date(2029, 7, 15) - date(2024, 12, 31)).days, 365)
    assert horizon == Fraction(1657, 365)
    benchmark = Fraction("0.0427") + (horizon - 3) / 2 * (Fraction("0.0438") - Fraction("0.0427"))
    assert benchmark == Fraction(frozen["benchmark"]["interpolated_yield_exact"])

    # Explicit analyst 30E/360 dates and past July 2024 coupon, not a dealer convention.
    def days360(end):
        return 360 * (end.year - 2024) + 30 * (end.month - 12) + min(end.day, 30) - 30

    dates = [date(y, m, 15) for y in range(2025, 2030) for m in (1, 7)]
    assert dates[-1] == date(2029, 7, 15)
    coupon = Fraction("5.95") / 2
    maturity = [(Fraction(days360(d), 360), coupon + (100 if d == dates[-1] else 0)) for d in dates]
    call = maturity[:-1] + [
        (Fraction(days360(date(2029, 6, 15)), 360), 100 + Fraction("5.95") * Fraction(150, 360))
    ]
    for label, flows in [("maturity_flows", maturity), ("par_call_flows", call)]:
        assert flows == [
            (Fraction(r["time_years_exact"]), Fraction(r["amount_per100_exact"]))
            for r in frozen[label]
        ]
    accrued = Fraction("5.95") * Fraction(165, 360)
    assert accrued == Fraction(frozen["exact_accrued_per100"]) == Fraction(1309, 480)
    helper = (
        ROOT
        / "docs/reuse/selected-methods/skills/cp-3d-market-implied-risk/scripts/bond_analytics.py"
    )
    assert (
        hashlib.sha256(helper.read_bytes()).hexdigest()
        == "b51b375a1a1c0aff668f85a9550e2d272f5f9a9be142407a68ba7bced0d4bced"
    )
    spec = importlib.util.spec_from_file_location("selected_bond", helper)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):

        def dec(x):
            x = Fraction(x)
            return Decimal(x.numerator) / Decimal(x.denominator)

        def fmt(x):
            return (
                "—"
                if x is None
                else str((x if isinstance(x, Decimal) else dec(x)).quantize(Decimal(".000001")))
            )

        def pv(rate, flows):
            return sum(dec(cf) * (1 + rate / 2) ** (-2 * dec(t)) for t, cf in flows)

        floatflows = [(float(t), float(cf)) for t, cf in maturity]
        callflows = [(float(t), float(cf)) for t, cf in call]
        controls = []
        actual = []
        lossrows = []
        shockrows = []
        equivalent = Fraction(861, 850) * 100
        for name, previous in frozen["results"].items():
            isclean = name.startswith("A_")
            dirty = equivalent + accrued if isclean else equivalent
            clean = equivalent if isclean else equivalent - accrued
            assert dirty == Fraction(previous["dirty_price_used"]) and clean == Fraction(
                previous["assumed_clean_price"]
            )
            y = module.yield_to(float(dirty), floatflows)
            cy = module.yield_to(float(dirty), callflows)
            # Frozen independent high-precision roots are verified by PV, not trusted as flags.
            exact = Decimal(previous["independent_decimal_maturity_yield"])
            call_exact = Decimal(previous["independent_decimal_par_call_yield"])
            assert abs(pv(exact, maturity) - dec(dirty)) < Decimal("1e-38")
            assert abs(pv(call_exact, call) - dec(dirty)) < Decimal("1e-38")
            assert abs(Decimal(str(y)) - exact) < Decimal("1e-9") and abs(
                Decimal(str(cy)) - call_exact
            ) < Decimal("1e-9")
            spread = exact - dec(benchmark)
            duration = sum(
                dec(cf) * dec(t) * (1 + exact / 2) ** (-2 * dec(t) - 1) for t, cf in maturity
            ) / dec(dirty)
            dv01 = duration * dec(dirty) / 10000
            assert abs(
                duration - Decimal(str(previous["modified_duration_under_maturity_scenario"]))
            ) < Decimal("1e-8")
            controls.append(
                [
                    name,
                    fmt(equivalent),
                    fmt(dirty),
                    fmt(clean),
                    fmt(accrued),
                    fmt(exact),
                    fmt(call_exact),
                    fmt(min(exact, call_exact)),
                    fmt(spread * 10000),
                    fmt(duration),
                    fmt(dv01),
                ]
            )
            shocks = []
            for shock, prior in zip([-100, 100], previous["yield_shocks"], strict=True):
                projected = pv(exact + Decimal(shock) / 10000, maturity) - (
                    dec(accrued) if isclean else 0
                )
                out = module._pv(y + shock / 10000, floatflows) - (float(accrued) if isclean else 0)
                assert abs(Decimal(str(out)) - projected) < Decimal("1e-8")
                assert abs(projected - Decimal(prior["exact_decimal_expected_price"])) < Decimal(
                    "1e-35"
                )
                shockrows.append(
                    [
                        f"{name}_{shock}",
                        fmt(projected),
                        fmt(projected - dec(equivalent)),
                        fmt((projected / dec(equivalent) - 1) * 100),
                    ]
                )
                shocks.append({"change_bps": shock, "equivalent_price": out})
            for recovery, prior in zip(
                [Fraction(1, 5), Fraction(2, 5), Fraction(3, 5)],
                previous["default_loss_break_even_sensitivity"],
                strict=True,
            ):
                annual = spread / (1 - dec(recovery))
                cumulative = 1 - (1 - annual) ** dec(horizon)
                assert abs(annual - Decimal(prior["decimal_expected_annual"])) < Decimal("1e-35")
                assert abs(cumulative - Decimal(prior["decimal_expected_cumulative"])) < Decimal(
                    "1e-35"
                )
                lossrows.append(
                    [name + "_" + str(recovery), fmt(recovery), fmt(annual), fmt(cumulative)]
                )
            rounding = []
            for change, prior in zip(
                [Fraction(-1, 2), Fraction(1, 2)],
                previous["rounded_source_fair_value_yield_range"],
                strict=True,
            ):
                p = (Fraction(861) + change) / 850 * 100 + (accrued if isclean else 0)
                result = module.yield_to(float(p), floatflows)
                assert abs(pv(Decimal(str(result)), maturity) - dec(p)) < Decimal("1e-8")
                assert abs(result - prior) < 1e-10
                rounding.append(result)
            actual.append(
                {
                    "case": name,
                    "dirty_price_exact": str(dirty),
                    "assumed_clean_price_exact": str(clean),
                    "maturity_yield": y,
                    "par_call_yield": cy,
                    "simple_spread_bps": (y - float(benchmark)) * 10000,
                    "modified_duration": sum(
                        cf * t * (1 + y / 2) ** (-2 * t - 1) for t, cf in floatflows
                    )
                    / float(dirty),
                    "loss_break_even_sensitivities": [
                        {
                            "recovery_fraction": r,
                            "annual_fraction": (y - float(benchmark)) / (1 - r),
                            "horizon_fraction": 1
                            - (1 - (y - float(benchmark)) / (1 - r)) ** float(horizon),
                        }
                        for r in (0.2, 0.4, 0.6)
                    ],
                    "rounding_yield_bounds": rounding,
                    "shocks": shocks,
                }
            )
        curvegrid = {
            "heading": "Evaluated curve controls",
            "columns": [
                "Series",
                "Principal_USDm",
                "Carrying_USDm",
                "Fair_USDm",
                "Equivalent_per100",
                "Prior_equivalent_per100",
                "Change_points",
            ],
            "rows": [[*r[:4], *[fmt(x) for x in r[4:]]] for r in rows],
        }
        grids = [
            curvegrid,
            {
                "heading": "Conditional pricing controls",
                "columns": [
                    "Case",
                    "Equivalent",
                    "Dirty",
                    "Clean",
                    "Accrued",
                    "Maturity_yield_fraction",
                    "Par_call_yield_fraction",
                    "Minimum_two_legs_fraction",
                    "Simple_spread_bps",
                    "Modified_duration",
                    "DV01",
                ],
                "rows": controls,
            },
            {
                "heading": "Loss break-even controls",
                "columns": [
                    "Case_recovery",
                    "Recovery_fraction",
                    "Annual_loss_fraction",
                    "Horizon_loss_fraction",
                ],
                "rows": lossrows,
            },
            {
                "heading": "Yield shock controls",
                "columns": [
                    "Case_shock_bps",
                    "Equivalent_price",
                    "Change_points",
                    "Change_percent",
                ],
                "rows": shockrows,
            },
        ]
    for payload in [
        {"price": 100, "coupon": 5.95, "years_to_maturity": 5, "settlement_date": "2024-12-31"},
        {
            "price": 100,
            "coupon": 5.95,
            "years_to_maturity": 5,
            "convention": {"day_count": "30E/360"},
        },
    ]:
        try:
            module.compute(payload)
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported general dated convention accepted")
    assert module.yield_to(None, floatflows) is None and module.yield_to(0, floatflows) is None
    return {
        "scope": "Fresh unchanged low-level yield/PV calls on explicitly chosen30E/360flows; independent50digitDecimalPV/derivatives/shocks/losschecks against primarysourceoperands and retainedindependentroots. High-leveldated/30E360refusals preserved. Notgeneraldatedadapter,executablequote,OASorcurrentrisk.",
        "valuation_date": "2024-12-31",
        "curve": frozen["raw_source_curve"],
        "accrued_exact": str(accrued),
        "maturity_flows": frozen["maturity_flows"],
        "par_call_flows": frozen["par_call_flows"],
        "horizon_act365f": str(horizon),
        "benchmark_yield_exact": str(benchmark),
        "cases": actual,
        "checked_numeric_cells": sum(len(r) - 1 for g in grids for r in g["rows"]),
    }, grids
