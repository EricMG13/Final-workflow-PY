"""Offline CP-8 publication, input identity and provider-refusing resume checks."""

import hashlib
import json
import runpy
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from deploy_vii.contracts import View
from deploy_vii.report_view import ReportView
from deploy_workflow.model.adapter import LiveAdapter
from deploy_workflow.owners.cpos import run_live_comparison

CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[2]


def verify():
    state = CASE / "execution"
    completions = list(state.glob("completed-*.json"))
    assert len(completions) == 1
    completion = json.loads(completions[0].read_bytes())
    assert completion["execution"] == "live-provider"
    report = state / "deliveries" / completion["delivery_id"] / "report.html"
    raw = (state / completion["response"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == completion["response_sha256"]
    assert (report.parent / "CP-8.md").read_bytes() == raw
    assert hashlib.sha256(report.read_bytes()).hexdigest() == completion["report_sha256"]
    rv = ReportView.model_validate_json((report.parent / "report-view.json").read_bytes())
    assert [r.label for r in rv.blocks[0].rows] == [
        "Values",
        "Periods",
        "Assumptions",
        "Conclusions",
        "Sources",
        "Limitations",
        "Output scope",
    ]
    view = View.model_validate_json((report.parent / "view.json").read_bytes())
    lines = raw.decode().splitlines()
    for fact in view.modules[0].facts:
        for citation in fact.citations:
            assert citation.source_sha256 == completion["response_sha256"]
            assert citation.quote == lines[int(citation.locator.split()[-1]) - 1]
    for name in ("prior/delivery.json", "current/delivery.json"):
        assert completion["input_files"][name] in raw.decode()
    before = (state / "live/calls.jsonl").read_bytes()
    calls = [json.loads(line) for line in before.decode().splitlines()]
    for call in calls:
        assert call["reported_model"] == "gpt-6.1-sol"
        assert call["requested_effort"] == "medium" and call["http_status"] == 200
        assert call["module_id"] == "CP-8" and call["error_class"] is None
    cost = sum((Decimal(c["settled_usd"]) for c in calls), Decimal(0))
    assert cost <= Decimal(completion["provider_cap_usd"])
    check = runpy.run_path(str(CASE / "run.py"))["check"]
    with patch.object(LiveAdapter, "complete", side_effect=AssertionError("Provider on resume")):
        resumed = run_live_comparison(
            CASE / "comparison.json",
            state,
            ruling=ROOT / "docs/rulings/2026-11-05-remaining-modules.md",
            check=check,
            environ={},
            max_turns=24,
            max_output_tokens=16000,
        )
    assert resumed == report and (state / "live/calls.jsonl").read_bytes() == before
    assert not list(report.parent.glob("*.xlsx"))
    return {
        "report": str(report.relative_to(CASE.parent)),
        "handoff_sha256": completion["response_sha256"],
        "report_sha256": completion["report_sha256"],
        "calls": len(calls),
        "cost_usd": str(cost),
        "verification": "Seven dimensions published from actual response; every citation line/hash exact; both complete input bundles revalidated; zero-provider resume preserves publication and call log.",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
