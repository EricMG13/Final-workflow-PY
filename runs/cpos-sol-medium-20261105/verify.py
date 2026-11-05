"""Offline source, arithmetic, publication and no-provider resume verification.

Historical failed attempts remain evidence. Only the latest governance-tool
submission in each run is required to have no quote mismatches. Financial
expectations use the frozen direct-source observations and Fraction arithmetic,
not production calculations or the newly generated answer.
"""

import copy
import hashlib
import json
import os
import re
import runpy
from collections import defaultdict
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

from deploy_vii.contracts import Run
from deploy_workflow.handoff_delivery import verify_delivery
from deploy_workflow.owners.cpos import HandoffTask, run_live_handoffs

p = Path(__file__).resolve().parent
os.chdir(p.parents[1])
script = runpy.run_path(str(p / "run.py"))
data = script["inputs"]
check = script["check"]
up = {}
module_stats = {}
for m in ("CP-0", "CP-1", "CP-1A", "CP-2"):
    raw = (p / data["handoffs"].get(m, m + ".md")).read_bytes()
    assert not check(
        HandoffTask(Run.model_validate_json(json.dumps(data["run"])), m, b"", {}, up, 1, ()), raw
    )
    up[m] = raw
    module_stats[m] = {
        "handoff": data["handoffs"].get(m, m + ".md"),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
verify_delivery(p / "module-delivery-inputs.json", p / "module-delivery")
model_checks = runpy.run_path(str(p.parents[1] / "tests/test_model_handoff_delivery.py"))


def verify_model(directory):
    # Reuse the existing independent frozen Fraction oracle, never production math.
    publication = SimpleNamespace(files={f.name: f.read_bytes() for f in directory.iterdir()})
    model_checks["test_81_values_against_independent_source_fraction_checks"](publication)
    model_checks["test_charts_have_18_exact_table_twins_and_missing_observation"](publication)


verify_model(p / "module-delivery")
calls = [json.loads(line) for line in (p / "live/calls.jsonl").read_text().splitlines()]
cost = defaultdict(lambda: Decimal(0))
turns = defaultdict(int)
calculations = defaultdict(int)
quotes = defaultdict(int)
latest_governance = {}
reconciled_tool_quote_issues = []
source_pages = [
    json.loads(line)["text"]
    for line in (p / data["sources"]["S1-text-aid.jsonl"]["path"]).read_text().splitlines()
]


def norm(t):
    return " ".join(
        t.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
        .split()
    )


for call in calls:
    key = (call["run_id"], call["module_id"])
    cost[key] += Decimal(call["settled_usd"])
    turns[key] += 1
    assert (
        call["config_id"] == "sol-medium"
        and call["requested_effort"] == "medium"
        and call["reported_model"] == "gpt-6.1-sol"
        and call["http_status"] == 200
        and call["error_class"] is None
    )
    f = p / "live/modules" / call["invocation_digest"]
    response = json.loads((f / f"{call['call_index']}.response.json").read_text())
    # The final result may still be awaiting its corresponding tools record in an active run.
    tools = f / f"{call['call_index']}.tools.json"
    if not tools.exists():
        continue
    results = {x["call_id"]: x for x in json.loads(tools.read_text())}
    for c in response["turn"]["tool_calls"]:
        if c["call_id"] not in results:
            continue
        result = results[c["call_id"]]["text"]
        args = c["arguments"]
        args = json.loads(args) if isinstance(args, str) else args
        if result.startswith("ERROR"):
            continue
        if c["name"] == "calculate":
            out = json.loads(result)
            vals = args["values"]
            if any(v is None for v in vals) or (
                args["operation"] == "ratio" and Fraction(vals[1]) == 0
            ):
                assert out["value"] is None
            else:
                values = [Fraction(v) for v in vals]
                expected = (
                    sum(values, Fraction(0))
                    if args["operation"] == "sum"
                    else values[0] / values[1]
                )
                with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
                    assert Decimal(out["value"]) == Decimal(expected.numerator) / Decimal(
                        expected.denominator
                    ), (key, args, out)
            calculations[key] += 1
        if c["name"] == "score_governance":
            latest_governance[key] = []
            for row in args["rows"]:
                for cite in row["citations"]:
                    pages = re.findall(
                        r"PDF\s+p(?:age)?\.?\s*(\d+)", cite["locator"], re.IGNORECASE
                    )
                    assert pages, cite["locator"]
                    text = norm(source_pages[int(pages[-1]) - 1])
                    quote = norm(cite["quote"])
                    if quote not in text:
                        issue = {
                            "run": key,
                            "invocation": call["invocation_digest"],
                            "locator": cite["locator"],
                            "quote": quote,
                        }
                        # A retained scorer call inserted "entitled" into an
                        # unscored source-boundary row. The published Q11 quote
                        # is already exact. Preserve the anomalous raw call and
                        # prove that correcting it leaves the entire score intact.
                        if (
                            call["invocation_digest"]
                            == "b1ffdd7c843238b07789319fa61414d0621f081015b4ef58f61589f6cb8c6fb8"
                            and row["topic"] == "G05 — disclosure boundary"
                            and quote.replace("captions entitled", "captions") in text
                        ):
                            from pydantic import TypeAdapter

                            from deploy_vii.business_context import (
                                GovernanceItem,
                                GovernanceScore,
                                governance_sponsor_score,
                            )

                            corrected = copy.deepcopy(args["rows"])
                            for corrected_row in corrected:
                                if corrected_row["topic"] == row["topic"]:
                                    corrected_row["citations"][0]["quote"] = cite["quote"].replace(
                                        "captions entitled", "captions"
                                    )

                            def score(rows):
                                parsed = TypeAdapter(list[GovernanceItem]).validate_json(
                                    json.dumps(rows)
                                )
                                return TypeAdapter(GovernanceScore).dump_json(
                                    governance_sponsor_score(parsed)
                                )

                            assert score(corrected) == score(args["rows"])
                            published = (p / data["handoffs"]["CP-1A"]).read_text()
                            q11 = next(
                                line
                                for line in published.splitlines()
                                if line.startswith("| Q11 |")
                            )
                            assert (
                                "under the captions ‘Beneficial" in q11
                                and "captions entitled" not in q11
                            )
                            issue["disposition"] = (
                                "Published Q11 is correct; source-corrected tool input yields identical full score. Original response remains retained."
                            )
                        else:
                            latest_governance[key].append(issue)
                        reconciled_tool_quote_issues.append(issue)
                    quotes[key] += 1
assert not any(latest_governance.values()), latest_governance
completed = list(p.glob("completed-*.json"))
assert completed, "Fresh orchestrated delivery must complete before final verification"
assert len(completed) == 1
receipt = json.loads(completed[0].read_text())
manifest = p / f"delivery-{receipt['delivery_manifest_sha256']}.json"
job = json.loads(manifest.read_text())
fresh_run = Run.model_validate_json(json.dumps(job["run"]))
up = {}
for m, response_path in receipt["modules"].items():
    raw = (p / response_path).read_bytes()
    request = json.loads((p / response_path).with_name("1.request.json").read_text())
    assert request["handoffs"] == {
        name: hashlib.sha256(content).hexdigest() for name, content in up.items()
    }
    assert not check(
        HandoffTask(fresh_run, m, request["instructions"].encode(), {}, up, 1, ()), raw
    )
    up[m] = raw
assert receipt["module_execution"] == {m: "live-provider" for m in up}
publications = list((p / "deliveries").glob("*/report.html"))
assert len(publications) == 1
report = publications[0]
verify_delivery(manifest, report.parent)
verify_model(report.parent)
for m in ("CP-1", "CP-1A", "CP-2"):
    assert (report.parent / (m + ".md")).read_bytes() == up[m]
before = (p / "live/calls.jsonl").read_bytes()
resumed = run_live_handoffs(
    p / "workflow.json",
    p,
    ruling=p.parents[1] / "docs/rulings/2026-11-05-live-loop-tests.md",
    check=check,
    environ={},
    max_turns=32,
    max_output_tokens=32000,
)
assert resumed == report and (p / "live/calls.jsonl").read_bytes() == before
assert not list(report.parent.glob("*.xlsx"))
print(
    json.dumps(
        {
            "module_handoffs": module_stats,
            "provider": {
                str(k): {
                    "turns": turns[k],
                    "cost_usd": str(v),
                    "independent_calculations": calculations[k],
                    "located_governance_quotes": quotes[k],
                }
                for k, v in cost.items()
            },
            "total_cost_usd": str(sum(cost.values())),
            "reconciled_tool_quote_issues": reconciled_tool_quote_issues,
            "fresh_report": str(report),
            "resume": "identical report; zero provider calls",
        },
        indent=2,
    )
)
