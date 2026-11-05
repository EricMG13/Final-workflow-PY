"""Read-only historical Ford ratings source/arithmetical and synthetic helper checks."""

import hashlib
import importlib.util
import json
import re
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from deploy_workflow.owners.cp2h import headroom, is_reached

ROOT = Path(__file__).resolve().parents[2]


def check():
    base = ROOT / "runs/ford-otosan-2024-001"
    finances = json.loads((base / "financial-calculations.json").read_bytes())
    controls = json.loads((base / "CP-2H-calculations.json").read_bytes())
    source = json.loads((base / "sources/fitch-and-metrics.json").read_bytes())
    # Restrict the repeated line namespace to the S&P document.
    source = source[source.index("Research Update:") :]
    for metric, lines in finances["source_line_map"].items():
        for line, expected in zip(lines, finances["values"][metric], strict=True):
            literal = re.findall(r"^L" + str(line) + r": (.+)$", source, re.MULTILINE)
            assert len(set(literal)) == 1, (metric, line)
            assert (None if literal[0] == "--" else literal[0].replace(",", "")) == expected
    rows = []
    for i, year in enumerate((2023, 2024, 2025)):
        values = {
            k: None if v[i] is None else Fraction(v[i]) for k, v in finances["values"].items()
        }
        ratios = [
            values["debt_sp"] / values["ebitda_sp"],
            values["ffo"] / values["debt_sp"],
            values["ebitda_sp"] / values["revenue"],
        ]
        assert (
            values["ffo"]
            == values["ebitda_sp"] + values["cash_interest_signed"] + values["cash_tax_signed"]
        )
        # Known-numeric subtotal only: absent disposal rows remain absent in source data.
        residual = values["ebitda_sp"] - sum(
            values[k]
            for k in ("ebitda_reported", "capitalised_development_signed", "disposal_adjustment")
            if values[k] is not None
        )
        dcf_residual = values["dcf"] - (values["focf"] - values["dividends"])
        assert residual == (-1, 0, 0)[i] and dcf_residual == (0, 1, 0)[i]
        with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
            for expected, key in zip(
                ratios,
                ("leverage_calculated", "ffo_debt_calculated", "margin_calculated"),
                strict=True,
            ):
                assert Decimal(finances["calculations"][i][key]) == Decimal(
                    expected.numerator
                ) / Decimal(expected.denominator)
        with localcontext(Context(prec=60, rounding=ROUND_HALF_EVEN)):
            rows.append(
                [
                    str(year),
                    *[
                        str(
                            (Decimal(x.numerator) / Decimal(x.denominator)).quantize(
                                Decimal(".000001")
                            )
                        )
                        for x in ratios
                    ],
                    str(residual),
                    str(dcf_residual),
                ]
            )
    for probe in controls["synthetic_boundary_controls"]:
        args = {
            "comparison": probe["comparison"],
            "metric": Decimal(probe["metric"]),
            "threshold": Decimal(probe["threshold"]),
        }
        actual = headroom(**args, unit_class=probe["unit"])
        expected = Fraction(probe["threshold"]) - Fraction(probe["metric"])
        if probe["comparison"] == "Below":
            expected = -expected
        if probe["unit"] == "percent":
            expected *= 100
        assert Fraction(actual) == expected == Fraction(probe["headroom"])
        assert is_reached(**args) is probe["strict_reached"]
    path = (
        ROOT
        / "docs/reuse/selected-methods/skills/cp-2h-ratings-migration-trigger/scripts/covenant_headroom.py"
    )
    spec = importlib.util.spec_from_file_location("selected_rating_headroom", path)
    # The selected rating excerpt omits its shared parser validator. Reuse the
    # byte-identical already-vendored dependency; never write to the predecessor.
    shared = ROOT / "docs/reuse/selected-methods/skills/cp-1c-peer-benchmark/scripts"
    assert hashlib.sha256((shared / "validate_handoff.py").read_bytes()).hexdigest() == (
        "c640aaaf579907c63a72d5a5a0df5134ed89dbf273441846ec399353e3bbac9e"
    )
    sys.dont_write_bytecode = True
    sys.path.append(str(shared))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    probes = {
        "repeated_without_rule": {
            "trigger": "synthetic margin control",
            "trigger_direction": "min-ratio",
            "threshold": "0.06",
            "cases": [{"period": y, "case": "D", "value": "0.055"} for y in ("2024", "2025")],
        },
        "explicit_same_case_rule": {
            "trigger": "synthetic margin control",
            "trigger_direction": "min-ratio",
            "threshold": "0.06",
            "cases": [{"period": y, "case": "D", "value": "0.055"} for y in ("2024", "2025")],
            "sustained_periods": ["2024", "2025"],
        },
        "split_cases_not_duration": {
            "trigger": "synthetic margin control",
            "trigger_direction": "min-ratio",
            "threshold": "0.06",
            "cases": [
                {"period": "2024", "case": "A", "value": "0.055"},
                {"period": "2025", "case": "B", "value": "0.055"},
            ],
            "sustained_periods": ["2024", "2025"],
        },
        "range_endpoints": {
            "trigger": "synthetic range control",
            "trigger_direction": "max-ratio",
            "threshold_lower": "2",
            "threshold_upper": "2.2",
            "cases": [{"period": "P", "case": "X", "value": "2.1"}],
        },
    }
    for name, probe in probes.items():
        assert module.trigger_headroom(probe) == controls["synthetic_duration_controls"][name]
    assert [controls["synthetic_duration_controls"][k]["sustained"] for k in probes] == [
        None,
        True,
        None,
        False,
    ]
    assert controls["reported_fitch_central_illustration"]["strict_reached"] is None
    assert controls["sp_geography_proxy"]["true_agency_headroom"] is None
    return {
        "execution": "Read-only source-literal and Fraction recheck; six unchanged pure headroom/boundary calls and four selected duration helper calls. Synthetic controls are not issuer forecasts.",
        "verified_primary_cells": 51,
        "financials": {
            k: finances[k] for k in ["selected_source", "values", "calculations", "limits"]
        },
        "controls": {
            k: controls[k]
            for k in [
                "reported_fitch_central_illustration",
                "sp_geography_proxy",
                "ordinal_symbol_distance",
                "synthetic_boundary_controls",
                "synthetic_duration_controls",
            ]
        },
    }, {
        "heading": "Financial definition controls",
        "columns": [
            "Year",
            "SP debt/EBITDA",
            "FFO/debt fraction",
            "EBITDA margin fraction",
            "Known EBITDA residual TRY m",
            "DCF residual TRY m",
        ],
        "rows": rows,
    }


def check_funding():
    """Independently check the separate rounded 2024 plan, not adjusted forecast cash flow."""
    from deploy_workflow.owners.cp3c import Gap, _diff, _ratio, _total

    base = ROOT / "runs/ford-otosan-2024-001"
    expected = json.loads((ROOT / "runs/cpos-ford-funding-2024-001/expectations.json").read_bytes())
    old = json.loads((base / "CP-3C-intake-calculations.json").read_bytes())
    source = json.loads((base / "sources/fitch-and-metrics.json").read_bytes())
    for line, literal in [
        (486, "15.2"),
        (488, "63"),
        (490, "16"),
        (492, "15"),
        (495, "33.8"),
        (497, "8.6"),
        (499, "2"),
        (501, "46.3"),
        (502, "15%"),
        (504, "27.1"),
    ]:
        matches = re.findall(r"^L" + str(line) + r": (.+)$", source, re.MULTILINE)
        assert len(matches) == 1 and literal in matches[0]
    sources = sum(map(Fraction, expected["sources_try_bn"].values()))
    uses = sum(map(Fraction, expected["uses_try_bn"].values()))
    source_cases = [sources, sources - 16, sources - 15, sources - 31, sources, sources]
    use_cases = [uses] * 4 + [uses + Fraction("27.1"), uses - Fraction("46.3") * Fraction(".15")]
    rows = []
    with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
        assert _total(map(Decimal, expected["sources_try_bn"].values())) == Decimal("109.2")
        assert _total(map(Decimal, expected["uses_try_bn"].values())) == Decimal("90.7")
        for s, u, prior in zip(source_cases, use_cases, old["conditional_cases"], strict=True):
            ds, du = (
                Decimal(s.numerator) / Decimal(s.denominator),
                Decimal(u.numerator) / Decimal(u.denominator),
            )
            ratio = _ratio(ds, du, "Nonpositive uses")
            difference = _diff(ds, du)
            exact_ratio = s / u
            rounded = (Decimal(exact_ratio.numerator) / Decimal(exact_ratio.denominator)).quantize(
                Decimal(".0001"), rounding=ROUND_HALF_UP
            )
            assert ratio == rounded == Decimal(prior["ratio_4dp"])
            assert Fraction(difference) == s - u == Fraction(prior["source_minus_use_try_bn"])
            assert ds == Decimal(prior["sources_try_bn"]) and du == Decimal(prior["uses_try_bn"])
            rows.append([prior["case"], str(ds), str(du), str(difference), str(ratio)])
        gap = Gap("No certified access")
        assert _total([Decimal("15.2"), gap]) == gap
        assert _ratio(gap, Decimal("90.7"), "Nonpositive uses") == gap
    return {
        "execution": "New offline unchanged total/difference/ratio helper calls, separately Fraction checked; approximate historical plan, not an actual financing outcome.",
        "source_components": expected["sources_try_bn"],
        "use_components": expected["uses_try_bn"],
        "cases": rows,
        "checks": "Ten primary literals, two totals, six ratios/balances and two missingness controls passed",
    }, {
        "heading": "Funding controls",
        "columns": ["Case", "Sources TRY bn", "Uses TRY bn", "Difference TRY bn", "Ratio"],
        "rows": rows,
    }


if __name__ == "__main__":
    output, grid = check()
    print(output["execution"], output["verified_primary_cells"])
    print(check_funding()[0]["checks"])
