"""Offline campaign checks; never launches a provider or chooses another module."""

import hashlib
import json
from collections import Counter
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parent


def audit_calls():
    counts = Counter()
    cost = Decimal(0)
    calculations = 0
    declined_ratios = 0
    for line in (CAMPAIGN / "live/calls.jsonl").read_text().splitlines():
        call = json.loads(line)
        assert call["config_id"] == "sol-medium"
        assert call["requested_effort"] == "medium"
        assert call["reported_model"] == "gpt-6.1-sol"
        assert call["http_status"] == 200 and call["error_class"] is None
        cost += Decimal(call["settled_usd"])
        counts[call["module_id"]] += 1
        directory = CAMPAIGN / "live/modules" / call["invocation_digest"]
        index = str(call["call_index"])
        response = json.loads((directory / (index + ".response.json")).read_bytes())
        tools = directory / (index + ".tools.json")
        assert tools.exists(), "Do not audit an active/incomplete module"
        results = {result["call_id"]: result["text"] for result in json.loads(tools.read_bytes())}
        for tool in response["turn"]["tool_calls"]:
            if tool["name"] != "calculate":
                continue
            args = json.loads(tool["arguments"])
            result = results[tool["call_id"]]
            assert not result.startswith("ERROR"), (tool, result)
            out = json.loads(result)
            values = args["values"]
            if any(v is None for v in values):
                assert out["value"] is None
            elif args["operation"] == "ratio" and Fraction(values[1]) <= 0:
                assert out["value"] is None
                assert out["reason"] == "ZERO_OR_NEGATIVE_DENOMINATOR"
                declined_ratios += 1
            else:
                numbers = list(map(Fraction, values))
                expected = (
                    sum(numbers, Fraction(0))
                    if args["operation"] == "sum"
                    else numbers[0] / numbers[1]
                )
                with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
                    assert Decimal(out["value"]) == Decimal(expected.numerator) / Decimal(
                        expected.denominator
                    ), (tool, out)
            calculations += 1
    return {
        "calls": dict(counts),
        "cost_usd": str(cost),
        "independent_calculations": calculations,
        "declined_nonpositive_ratios": declined_ratios,
    }


def publish(task_path):
    """Publish this explicitly selected reviewed module through existing delivery."""
    from deploy_workflow.handoff_delivery import deliver, verify_delivery
    from deploy_workflow.workflow import _put

    task_path = task_path.resolve()
    spec = json.loads(task_path.read_bytes())
    base = task_path.parent
    raw = (base / spec["output"]).read_bytes()
    manifest = base / (spec["module_id"] + ".delivery.json")
    data = {
        "run": spec["run"],
        "handoffs": {
            spec["module_id"]: {"path": spec["output"], "sha256": hashlib.sha256(raw).hexdigest()}
        },
        "layout": json.loads((base / spec["layout"]).read_bytes()),
    }
    _put(manifest, json.dumps(data, indent=2).encode() + b"\n")
    destination = base / (spec["module_id"] + "-delivery")
    if not destination.exists():
        deliver(manifest, destination)
    verify_delivery(manifest, destination)
    assert (destination / (spec["module_id"] + ".md")).read_bytes() == raw
    return str((destination / "report.html").relative_to(CAMPAIGN))


if __name__ == "__main__":
    print(json.dumps(audit_calls(), indent=2))
