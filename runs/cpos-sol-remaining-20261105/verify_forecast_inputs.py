"""Single selected forecast fixture: independent rational checks, no provider/old-run writes."""

import json
from dataclasses import fields, replace
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from deploy_workflow.owners.cp2g import (
    BreakTest,
    Drivers,
    Operands,
    Val,
    Year,
    forecast,
    fy_periods,
    require_calendar,
    test_breaks,
)
from deploy_workflow.owners.period_basis import DEFAULT_BASIS, PeriodRefused

ROOT = Path(__file__).resolve().parents[2]


def check():
    assumptions = json.loads((ROOT / "runs/cpos-tdg-forecast-001/expectations.json").read_bytes())
    old = json.loads((ROOT / "runs/tdg-003/CP-2G-attempt-1-calculations.json").read_bytes())
    basis = replace(
        DEFAULT_BASIS,
        base_year=2024,
        years=(2025, 2026, 2027),
        ltm_start=date(2023, 10, 1),
        ltm_end=date(2024, 9, 30),
    )
    try:
        require_calendar(basis)
    except PeriodRefused as error:
        refusal = str(error)
    else:
        raise AssertionError("Fiscal wrapper must still refuse September dates")
    assert refusal == old["calendar_diagnostic"]["actual_refusal"]
    assert list(fy_periods(basis)) == old["calendar_diagnostic"]["actual_wrapper_labels"]
    operands = Operands(
        **{
            k: Val(None if v["amount"] is None else Decimal(v["amount"]), v["reason"])
            for k, v in old["base"].items()
        }
    )
    for name, expected in [
        ("revenue", "7940"),
        ("ebitda", "4173"),
        ("interest", "1158"),
        ("taxes", "539"),
        ("capex", "165"),
        ("debt", "24880"),
        ("cash", "6261"),
    ]:
        assert getattr(operands, name).amount == Decimal(expected)
    for name in ("undrawn", "wc", "fcf"):
        assert getattr(operands, name).amount is None
    grids, cases = [], {}
    for case in ("REFERENCE", "DOWNSIDE", "UPSIDE"):
        drivers = Drivers(
            **{
                k: tuple(map(Decimal, v))
                for k, v in old[
                    "upside_drivers" if case == "UPSIDE" else "reference_drivers"
                ].items()
            }
        )
        shock = (Decimal(".20"), Decimal(".10")) if case == "DOWNSIDE" else None
        actual = forecast(operands=operands, drivers=drivers, shock=shock)
        # Independent expected amounts from frozen source/assumption literals, no engine intermediates.
        money = assumptions["base"]
        revenue, debt, cash = map(Fraction, (money["revenue"], money["debt"], money["cash"]))
        expected_years = []
        for t in range(3):
            rev = revenue * (1 + Fraction(assumptions["growth"][t]))
            earnings = rev * Fraction(
                assumptions["upside_margin" if case == "UPSIDE" else "reference_margin"]
            )
            interest = debt * Fraction(assumptions["cash_interest_rate"])
            if case == "DOWNSIDE":
                earnings *= 1 - Fraction(assumptions["downside_earnings_reduction"])
                interest *= 1 + Fraction(assumptions["downside_interest_increase"])
            tax_wc = rev * Fraction(assumptions["combined_tax_wc_share"])
            capex = rev * Fraction(assumptions["capex_share"])
            cfo = earnings - interest - tax_wc
            proxy = cfo - capex
            rep, dividend = (
                Fraction(assumptions["repayment"][t]),
                Fraction(assumptions["distributions"][t]),
            )
            end_debt, end_cash = debt - rep, cash + proxy - rep - dividend
            expected = {
                "revenue": rev,
                "ebitda": earnings,
                "interest": interest,
                "tax_wc": tax_wc,
                "capex": capex,
                "cfo": cfo,
                "fcf": proxy,
                "opening_debt": debt,
                "repayment": rep,
                "closing_debt": end_debt,
                "opening_cash": cash,
                "dividends": dividend,
                "closing_cash": end_cash,
                "undrawn": None,
                "liquidity": None,
                "total_leverage": end_debt / earnings,
                "net_debt": end_debt - end_cash,
                "net_leverage": (end_debt - end_cash) / earnings,
                "coverage": earnings / interest,
                "fcf_to_debt": proxy / end_debt,
            }
            expected_years.append(expected)
            for field in fields(Year):
                value = getattr(actual.years[t], field.name).amount
                prior = old["outputs"][case]["years"][t][field.name]["amount"]
                assert (None if value is None else str(value)) == prior
                oracle = expected[field.name]
                if oracle is None:
                    assert value is None
                else:
                    with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
                        assert value == Decimal(oracle.numerator) / Decimal(oracle.denominator)
            revenue, debt, cash = rev, end_debt, end_cash
        tests = [
            BreakTest(
                row,
                kind,
                row,
                None if threshold is None else Decimal(threshold),
                "No evidenced minimum liquidity or unconditional access"
                if threshold is None
                else None,
            )
            for row, kind, threshold in [
                ("proxy_zero", "fcf", "0"),
                ("one_coverage", "coverage", "1"),
                ("seven_leverage", "total_leverage", "7"),
                ("three_coverage", "coverage", "3"),
                ("minimum_liquidity", "liquidity", None),
            ]
        ]
        breaks = test_breaks(tests=tests, forecast=actual, basis=basis)
        for result, prior in zip(breaks, old["outputs"][case]["breaks"], strict=True):
            assert result.first == prior["first"] and list(result.hits) == prior["hits"]
            expected_hits = (
                [None, None, None]
                if result.row == "minimum_liquidity"
                else [
                    (
                        y["fcf"] <= 0
                        if result.row == "proxy_zero"
                        else y["coverage"] <= 1
                        if result.row == "one_coverage"
                        else y["total_leverage"] >= 7
                        if result.row == "seven_leverage"
                        else y["coverage"] <= 3
                    )
                    for y in expected_years
                ]
            )
            assert list(result.hits) == expected_hits
        rows = []
        for field in fields(Year):
            values = []
            for y in expected_years:
                x = y[field.name]
                with localcontext(Context(prec=60, rounding=ROUND_HALF_EVEN)):
                    values.append(
                        "—"
                        if x is None
                        else str(
                            (Decimal(x.numerator) / Decimal(x.denominator)).quantize(
                                Decimal(".000001")
                            )
                        )
                    )
            rows.append([field.name, *values])
        grids.append(
            {
                "heading": "Forecast controls " + case,
                "columns": ["Metric", "FY2025", "FY2026", "FY2027"],
                "rows": rows,
            }
        )
        cases[case] = {
            "years": [
                {
                    field.name: {
                        "amount": None
                        if getattr(y, field.name).amount is None
                        else str(getattr(y, field.name).amount),
                        "reason": getattr(y, field.name).reason,
                    }
                    for field in fields(Year)
                }
                for y in actual.years
            ],
            "breaks": [
                {"row": b.row, "hits": b.hits, "first": b.first, "reason": b.reason} for b in breaks
            ],
        }
        missing = forecast(
            operands=replace(operands, cash=Val(None, "Cash unavailable")),
            drivers=drivers,
            shock=shock,
        )
        assert all(
            y.closing_cash.amount is None
            and y.net_debt.amount is None
            and y.liquidity.amount is None
            and y.ebitda.amount is not None
            for y in missing.years
        )
    return {
        "execution": "New offline execution of unchanged pure forecast/break kernels; independent Fraction verification. Not a live model tool call or native fiscal wrapper acceptance.",
        "cases": cases,
        "calendar_refusal": refusal,
        "wrapper_labels": fy_periods(basis),
        "planning_windows": assumptions["planning_windows"],
        "source_midpoints": assumptions["source_midpoints"],
        "finite_driver_residuals": assumptions["driver_residuals"],
        "checks": "180 amounts including18missing,15first-break rows/45hits,three missing-cash controls; all passed",
    }, grids


if __name__ == "__main__":
    output, grids = check()
    print(output["checks"])
