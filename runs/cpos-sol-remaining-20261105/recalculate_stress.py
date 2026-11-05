"""Re-execute existing CP-2A math and independently check the frozen issuer case.

Provider-free fixture. This output is calculation evidence for live analysis,
not the independent expected key and not a model response.
"""

import hashlib
import json
from dataclasses import asdict, replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from deploy_workflow.owners.cp2a import (
    BaseOperands,
    ThresholdSpec,
    break_points,
    crossing,
    rank,
    stress,
)
from deploy_workflow.workflow import _put

ROOT = Path(__file__).resolve().parents[2]
CASE = Path(__file__).resolve().parent / "tdg-stress"
INPUT = ROOT / "runs/tdg-002/CP-2A-attempt-1-inputs.json"
inputs = json.loads(INPUT.read_bytes())
operands = inputs["base"]["operands"]
base = BaseOperands(
    period="FY24: 2023-10-01 to 2024-09-30",
    **{k: Decimal(v["value"]) for k, v in operands.items()},
    gates={},
    sources={},
)
# Frozen primary-source observations, independent of the production calculations.
assert [base.ebitda, base.interest, base.fcf, base.total_debt, base.cash] == [
    4173,
    1158,
    2045 - 165,
    24296 + 98 + 486,
    6261,
]
rows = []
for s, k in [("0", "0"), ("0.10", "0"), ("0.20", "0.10")]:
    result = stress(base=base, decline=Decimal(s), increase=Decimal(k))
    e = Fraction(4173) * (1 - Fraction(s))
    i = Fraction(1158) * (1 + Fraction(k))
    f = Fraction(1880) - 4173 * Fraction(s) - 1158 * Fraction(k)
    expected = {
        "ebitda": e,
        "interest": i,
        "fcf": f,
        "total_leverage": 24880 / e,
        "net_leverage": 18619 / e,
        "interest_coverage": e / i,
        "fcf_to_debt": f / 24880,
    }
    for field, rational in expected.items():
        with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
            assert getattr(result, field) == Decimal(rational.numerator) / Decimal(
                rational.denominator
            )
    rows.append((s, k, result))
points = break_points(
    base=base,
    thresholds=[
        ThresholdSpec("total_leverage", Decimal(7), "Analyst 7x carrying-debt watch"),
        ThresholdSpec("interest_coverage", Decimal(3), "Analyst 3x cash-interest watch"),
    ],
)
assert [p.required_exact for p in points] == [
    Fraction(1880, 4173),
    Fraction(4173 - 1158, 4173),
    1 - Fraction(24880, 7 * 4173),
    1 - Fraction(3 * 1158, 4173),
]
assert [p.break_id for p in rank(points)] == ["b03", "b04", "b01", "b02"]
assert [(r["ebitda_decline"], r["interest_increase"]) for r in inputs["scenarios"]] == [
    (s, k) for s, k, _ in rows
]
for s, _, result in rows:
    for point in points:
        expected_crossing = (
            "Crossed" if s == "0.20" and point.break_id in {"b03", "b04"} else "Not crossed"
        )
        assert crossing(point, result)[1] == expected_crossing
boundary = stress(base=replace(base, interest=Decimal(0)), decline=Decimal(0), increase=Decimal(0))
assert boundary.interest_coverage is None
assert "ZERO_OR_NEGATIVE_DENOMINATOR" in boundary.why["interest_coverage"]
missing = stress(base=replace(base, cash=None), decline=Decimal(0), increase=Decimal(0))
assert missing.net_leverage is None and missing.total_leverage is not None
code = ROOT / "src/deploy_workflow/owners/cp2a.py"
data = {
    "scope": "New deterministic re-execution of the existing static kernel; no provider/model/native-owner execution. Fixed illustrative assumptions, not calibrated forecasts.",
    "input_sha256": hashlib.sha256(INPUT.read_bytes()).hexdigest(),
    "code_sha256": hashlib.sha256(code.read_bytes()).hexdigest(),
    "base": inputs["base"],
    "scenarios": [
        {
            "decline": s,
            "increase": k,
            "result": asdict(r),
            "crossings": {p.break_id: crossing(p, r) for p in points},
        }
        for s, k, r in rows
    ],
    "breaks": [asdict(p) for p in points],
    "rank": [p.break_id for p in rank(points)],
    "controls": "21 flow/ratio values and four exact break fractions independently checked; zero-interest and missing-cash controls passed, separate from issuer scenarios.",
}
_put(
    CASE / "kernel-results.json",
    (
        json.dumps(
            data, indent=2, default=lambda v: sorted(v) if isinstance(v, frozenset) else str(v)
        )
        + "\n"
    ).encode(),
)
print(data["controls"])
