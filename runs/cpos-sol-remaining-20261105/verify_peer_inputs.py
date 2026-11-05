"""Read-only historical source/helper/oracle cross-check; no provider or writes."""

import importlib.util
import json
import sys
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

root = Path.cwd()
base = root / "runs/cpos-sol-remaining-20261105/tdg-peers"
assert base.is_dir()
old = root / "runs/tdg-peers-2024-001"
d = json.loads((old / "CP-1C-calculations.json").read_text())
v = json.loads((old / "verification.json").read_text())
for check in v["literal_source_checks"]:
    text = (root / check["source"]).read_text()
    assert check.get("actual_row", check.get("literal")).strip() in text
    if "independent_literal_expectation" in check:
        normalize = lambda s: " ".join(s.replace("$", "").split())
        assert normalize(check["independent_literal_expectation"]) in normalize(check["actual_row"])
method = root / "docs/reuse/selected-methods/skills/cp-1c-peer-benchmark"
helper = method / "scripts/peer_statistics.py"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("retained_peer_statistics", helper)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
results = {}
rows = []


def display(x):
    if x is None:
        return "—"
    x = Fraction(x)
    with localcontext() as c:
        c.prec = 70
        return str(
            (Decimal(x.numerator) / Decimal(x.denominator)).quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_EVEN
            )
        )


for key, item in d["results"].items():
    out = m.compute(item["input"])
    assert out == item["actual_unchanged_helper_output"]
    results[key] = {"input": item["input"], "actual_unchanged_helper_output": out}
    expected = next(
        x["exact_expected_statistics"]
        for x in d["independent_checks"]
        if key == x["period"] + "_" + x["metric"]
    )
    actual = out["statistics_including_outliers"]
    for stat, value in expected.items():
        if stat == "n":
            assert actual[stat] == value
        elif value is None:
            assert actual[stat] is None
        else:
            assert abs(Fraction(str(actual[stat])) - Fraction(value)) < Fraction(1, 10**10)
    rows.append(
        [
            key,
            str(expected["n"]),
            *[display(expected[x]) for x in ["minimum", "maximum", "range", "median"]],
        ]
    )
    for excluded in [False, True]:
        block = out["statistics_excluding_outliers"] if excluded else actual
        if block:
            assert all(block[x] is None for x in ["average", "q1", "q3", "stdev"])

retained = json.loads((base / "statistics-results.json").read_text())
assert retained["results"] == results
checks = json.loads((base / "CP-1C.checks.json").read_text())
assert checks["numeric_tables"][0]["rows"] == rows
print(
    "42 literal checks (32 source rows,10 retained borrower anchors);10 statistics and outlier suppressions independently verified"
)
