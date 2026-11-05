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
from deploy_workflow.owners.cpos import HandoffTask, _comparison_bundle

CASE = Path(__file__).resolve().parent
CAMPAIGN = CASE.parent
ROOT = CASE.parents[2]
STATE = CASE / "execution"


def verify() -> dict[str, object]:
    fixture = runpy.run_path(str(CASE / "run.py"))
    check = fixture["CHECK"]
    completed = list(STATE.glob("completed-*.json"))
    assert len(completed) == 1
    receipt = json.loads(completed[0].read_bytes())
    manifest = STATE / ("delivery-" + receipt["delivery_manifest_sha256"] + ".json")
    job = json.loads(manifest.read_bytes())
    run = Run.model_validate_json(json.dumps(job["run"]))
    order = ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-4", "CP-3", "CP-5", "CP-6"]
    assert list(receipt["modules"]) == order
    assert receipt["module_execution"] == {
        **dict.fromkeys(order, "live-provider"),
        "CP-0": "retained-response-replay",
        "CP-6": "retained-response-replay",
    }
    reviews = json.loads((CAMPAIGN / "verification.json").read_bytes())["recovery"]["reviews"]
    calls = [json.loads(line) for line in (STATE / "live/calls.jsonl").read_text().splitlines()]
    drafts = json.loads((CASE / "drafts.json").read_bytes())
    committee = (CASE / "CP-6.md").read_bytes()
    wording = CASE / "committee-wording"
    expected_committee = committee.decode()
    for edit in json.loads((wording / "edits.json").read_bytes()):
        assert expected_committee.count(edit["old"]) == 1
        expected_committee = expected_committee.replace(edit["old"], edit["new"])
    assert expected_committee.encode() == (wording / "CP-6.md").read_bytes()
    assert any(
        call["module_id"] == "CP-6"
        and call["reported_model"] == "gpt-6.1-sol"
        and call["requested_effort"] == "medium"
        and call["http_status"] == 200
        and any(tool["name"] == "edit_handoff" for tool in call["tool_calls"])
        and any(
            f.read_bytes() == expected_committee.encode()
            for f in (STATE / "live/modules" / call["invocation_digest"]).glob("*.draft.md")
        )
        for call in calls
    )
    upstream: dict[str, bytes] = {}
    for module, path in receipt["modules"].items():
        response = STATE / path
        raw = response.read_bytes()
        request = json.loads(response.with_name("1.request.json").read_bytes())
        assert request["handoffs"] == {
            m: hashlib.sha256(b).hexdigest() for m, b in upstream.items()
        }
        assert hashlib.sha256(raw).hexdigest() == reviews[module]["sha256"]
        assert not check(HandoffTask(run, module, b"", {}, upstream, 1, ()), raw)
        if module != "CP-0":
            submitted = committee if module == "CP-6" else raw
            if module == "CP-6":
                assert raw == expected_committee.encode()
            for digest in {c["invocation_digest"] for c in calls if c["module_id"] == module}:
                folder = STATE / "live/modules" / digest
                seed = json.loads((folder / "invocation.json").read_bytes())
                context = json.loads(seed["messages"][1]["text"])
                if context["run"] != job["run"] or context["sources"] != request["sources"]:
                    continue  # The two targeted committee repairs have their own context.
                assert seed["effort"] == "medium"
                assert context["handoffs"] == {
                    m: {"sha256": hashlib.sha256(b).hexdigest(), "markdown": b.decode()}
                    for m, b in upstream.items()
                }
                assert context["sources"] == request["sources"]
                if module in drafts:
                    assert context["repair_draft"]["sha256"] == drafts[module]["sha256"]
                else:
                    assert context["repair_draft"] is None
                assert any(f.read_bytes() == submitted for f in folder.glob("*.draft.md"))
                assert any(
                    c["invocation_digest"] == digest
                    and c["reported_model"] == "gpt-6.1-sol"
                    and c["http_status"] == 200
                    and any(t["name"] in {"edit_handoff", "write_handoff"} for t in c["tool_calls"])
                    for c in calls
                )
                break
            else:
                raise AssertionError(f"No matching actual provider submission for {module}")
        upstream[module] = raw
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
    reports = list((STATE / "deliveries").glob("*/report.html"))
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
    cash, maturity = figures[2].chart, figures[3].chart
    assert cash is not None and maturity is not None
    assert [m.value for m in cash.marks] == list(map(Decimal, [3001, 3472, 6261]))
    assert [m.value for m in maturity.marks] == [
        Decimal(93),
        Decimal(92),
        Decimal(92),
        Decimal(6637),
        Decimal(4768),
        Decimal(12637),
    ]
    assert (maturity.marks[2].ref_id or "").startswith("C")
    assert rv.call and rv.call[0].label == "Action bias" and rv.call_withheld is None
    bundle = report.parent / "delivery.json"
    _comparison_bundle(
        report.parent,
        HandoffInput(path=bundle.name, sha256=hashlib.sha256(bundle.read_bytes()).hexdigest()),
    )
    before = (STATE / "live/calls.jsonl").read_bytes()
    with patch.object(
        LiveAdapter, "complete", side_effect=AssertionError("Provider called on resume")
    ):
        resumed = fixture["run"](environ={})
    assert resumed == report and (STATE / "live/calls.jsonl").read_bytes() == before
    assert not list(report.parent.glob("*.xlsx"))
    return {
        "report": str(report.relative_to(CAMPAIGN)),
        "panels": 12,
        "handoff_hashes": {m: hashlib.sha256(b).hexdigest() for m, b in upstream.items()},
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "verification": "Checked retained CP-0 intake and seven sequential live TDG modules consumed the exact current handoffs; all12panels populated; every raw line/hash preserved; 81 independent Fraction expectations and18 Model chart twins; four report charts. Primary annual43/45/46 resolves November2027 as fiscal2028; reported FY2027 remains92. Complete CP8 bundle; provider-refusing resume identical.",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
