"""Offline exact publication checks and provider-refusing CP-OS resume."""

import hashlib
import json
import runpy
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from deploy_vii.contracts import Run, View
from deploy_vii.report_view import ReportView, pathways
from deploy_workflow.handoff_delivery import HandoffInput, verify_delivery
from deploy_workflow.model.adapter import LiveAdapter
from deploy_workflow.owners.cpos import HandoffTask, _comparison_bundle, run_live_handoffs

CASE = Path(__file__).resolve().parent
CAMPAIGN = CASE.parent
ROOT = CASE.parents[2]


def verify():
    check = runpy.run_path(str(CASE / "run.py"))["check"]
    completed = list(CAMPAIGN.glob("completed-*.json"))
    assert len(completed) == 1
    receipt = json.loads(completed[0].read_bytes())
    manifest = CAMPAIGN / ("delivery-" + receipt["delivery_manifest_sha256"] + ".json")
    job = json.loads(manifest.read_bytes())
    run = Run.model_validate_json(json.dumps(job["run"]))
    order = ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-4", "CP-3", "CP-5", "CP-6"]
    assert list(receipt["modules"]) == order
    assert receipt["module_execution"] == dict.fromkeys(order, "live-provider")
    reviews = json.loads((CAMPAIGN / "verification.json").read_bytes())["fresh_reviews"]
    upstream = {}
    for module, path in receipt["modules"].items():
        response = CAMPAIGN / path
        raw = response.read_bytes()
        request = json.loads(response.with_name("1.request.json").read_bytes())
        assert request["handoffs"] == {
            m: hashlib.sha256(b).hexdigest() for m, b in upstream.items()
        }
        assert hashlib.sha256(raw).hexdigest() == reviews[module]["sha256"]
        assert not check(HandoffTask(run, module, b"", {}, upstream, 1, ()), raw)
        upstream[module] = raw
    assurance = (CASE / "CP-5-before-instruction-review.md").read_text()
    for edit in json.loads((CASE / "CP-5.repair-edits.json").read_bytes()):
        assert assurance.count(edit["old"]) == 1
        assurance = assurance.replace(edit["old"], edit["new"])
    assert (CASE / "source-completion/CP-5.original.md").read_text() == assurance
    pages = {
        page["page"]: page["text"]
        for page in map(
            json.loads,
            (ROOT / "runs/cpos-tdg-fresh-001/source-pages.jsonl").read_text().splitlines(),
        )
    }
    assert "November 2027 (fiscal 2028)" in pages[43]
    assert "November 15, 2027" in pages[46] and "January 15, 2033" in pages[46]
    assert "$67 million in letters of credit outstanding" in pages[45]
    reports = list((CAMPAIGN / "deliveries").glob("*/report.html"))
    assert len(reports) == 1
    report = reports[0]
    verify_delivery(manifest, report.parent)
    view = View.model_validate_json((report.parent / "view.json").read_bytes())
    rv = ReportView.model_validate_json((report.parent / "report-view.json").read_bytes())
    assert tuple(b.block_id for b in rv.blocks) == next(
        p.blocks for p in pathways() if p.id == "credit_snapshot"
    )
    assert len(rv.blocks) == 12 and all(b.state == "populated" for b in rv.blocks)
    for module, raw in upstream.items():
        assert (report.parent / (module + ".md")).read_bytes() == raw
        lines = raw.decode().splitlines()
        for fact in next(m for m in view.modules if m.module_id == module).facts:
            for citation in fact.citations:
                assert citation.source_sha256 == hashlib.sha256(raw).hexdigest()
                assert citation.quote == lines[int(citation.locator.split()[-1]) - 1]
    checks = runpy.run_path(str(ROOT / "tests/test_model_handoff_delivery.py"))
    publication = SimpleNamespace(files={f.name: f.read_bytes() for f in report.parent.iterdir()})
    checks["test_81_values_against_independent_source_fraction_checks"](publication)
    checks["test_charts_have_18_exact_table_twins_and_missing_observation"](publication)
    figures = next(b for b in rv.blocks if b.block_id == "model-chart-strip").figures
    assert [f.fig_id for f in figures] == ["S.1", "S.2", "S.3", "S.4"]
    assert [m.value for m in figures[2].chart.marks] == list(map(Decimal, [3001, 3472, 6261]))
    assert [m.value for m in figures[3].chart.marks] == [
        Decimal(93),
        Decimal(92),
        Decimal(92),
        Decimal(6637),
        Decimal(4768),
        Decimal(12637),
    ]
    assert figures[3].chart.marks[2].ref_id.startswith("C")
    assert rv.call and rv.call[0].label == "Action bias" and rv.call_withheld is None
    bundle = report.parent / "delivery.json"
    _comparison_bundle(
        report.parent,
        HandoffInput(path=bundle.name, sha256=hashlib.sha256(bundle.read_bytes()).hexdigest()),
    )
    before = (CAMPAIGN / "live/calls.jsonl").read_bytes()
    with patch.object(
        LiveAdapter, "complete", side_effect=AssertionError("Provider called on resume")
    ):
        resumed = run_live_handoffs(
            CASE / "workflow.json",
            CAMPAIGN,
            ruling=ROOT / "docs/rulings/2026-11-05-remaining-modules.md",
            check=check,
            environ={},
            max_turns=32,
            max_output_tokens=24000,
        )
    assert resumed == report and (CAMPAIGN / "live/calls.jsonl").read_bytes() == before
    assert not list(report.parent.glob("*.xlsx"))
    return {
        "report": str(report.relative_to(CAMPAIGN)),
        "panels": 12,
        "handoff_hashes": {m: hashlib.sha256(b).hexdigest() for m, b in upstream.items()},
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "verification": "Eight fresh sequential modules with targeted live source-completeness corrections consumed exact current upstream bytes; all12panels populated; every raw line/hash preserved; 81 independent Fraction expectations and18 Model chart twins; four report charts. Primary annual43/45/46 resolves November2027 as fiscal2028; reported FY2027 remains92. Complete CP8 bundle; provider-refusing resume identical.",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
