"""Real retained handoff consumers; replay tests do not claim fresh model proof."""

import hashlib
import json
from pathlib import Path

import pytest

from deploy_vii.contracts import View
from deploy_vii.report_view import ReportView, _validate_cp1b_layout
from deploy_workflow.handoff_delivery import DeliveryRequest, delivery_files, verify_delivery
from deploy_workflow.markdown_delivery import literal_module
from deploy_workflow.owners.cpos import replay_handoffs, run_handoffs

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "runs/cpos-tdg-earnings-001"
ANSWERS = {
    "CP-0": ROOT / "runs/tdg-003/CP-0.md",
    "CP-1": ROOT / "runs/tdg-003/CP-1-attempt-2.md",
    "CP-1B": ROOT / "runs/tdg-003/CP-1B-attempt-1.md",
}


def job(tmp_path):
    data = json.loads((CASE / "workflow.json").read_bytes())
    for group in ("sources", "instructions", "retained_handoffs"):
        for item in data[group].values():
            item["path"] = str((CASE / item["path"]).resolve())
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(data))
    return path


def no_execution(task):
    pytest.fail(f"Rendering must not repeat analysis: {task.module_id}")


def check(task, response):
    assert response == ANSWERS[task.module_id].read_bytes()
    return ()


def test_real_earnings_response_consumed_by_report_and_resumed_without_model(tmp_path):
    manifest = job(tmp_path)
    state = tmp_path / "state"
    report = run_handoffs(manifest, state, execute=no_execution, check=check)
    view = View.model_validate_json((report.parent / "view.json").read_bytes())
    presented = ReportView.model_validate_json((report.parent / "report-view.json").read_bytes())
    assert [m.module_id for m in view.modules] == ["CP-0", "CP-1", "CP-1B"]
    for module, original in ANSWERS.items():
        assert (report.parent / (module + ".md")).read_bytes() == original.read_bytes()
    assert view.analytical_qualification == "partial"
    assert view.native_host_qualification == "unrun"
    blocks = {b.block_id: b for b in presented.blocks}
    assert len(blocks) == 5
    assert presented.call_withheld == "not_requested"
    headline = blocks["headline-results"]
    assert headline.columns == (
        "Prior",
        "Current",
        "Absolute change",
        "Change %",
        "Definition / source",
    )
    rows = {r.label: [c.text for c in r.cells] for r in headline.rows}
    assert rows["Revenue"] == ["1789", "2006", "217", "12.13%", "Reported sales"]
    assert rows["Capex signed cash flow"][:4] == ["-36", "-42", "-6", "16.67%"]
    assert rows["Closing cash"][:4] == ["4135", "2459", "-1676", "-40.53%"]
    assert "Medium confidence" in headline.tabs[0].rows[0].cells[0].text
    assert "No accepted budget" in blocks["guidance-signals"].lines[0].runs[0].text
    assert "organic +118 and acquisition +99" in blocks["variance-drivers"].lines[0].runs[0].text
    assert (
        "Quantified covenant/rating thresholds remain absent"
        in blocks["watch-items"].lines[0].runs[0].text
    )
    html = report.read_text()
    assert "89 days" in html and "91 days" in html
    assert "131" in html and "132" in html
    assert "not ordinary EBITDA margin" in html
    receipt = json.loads((report.parent / "delivery.json").read_bytes())
    assert receipt["excel_output"] is False
    assert receipt["analytical_runtime_executed"] is False
    assert {p.suffix for p in report.parent.iterdir()} == {".json", ".md", ".html"}
    assert verify_delivery(next(state.glob("delivery-*.json")), report.parent) == report
    assert replay_handoffs(manifest, state) == report
    assert len(list(state.glob("requests/*/*/*.response.md"))) == 3
    assert len(list(state.glob("completed-*.json"))) == 1


def test_presentation_change_reuses_all_analysis_and_preserves_previous_publication(tmp_path):
    manifest = job(tmp_path)
    state = tmp_path / "state"
    old = run_handoffs(manifest, state, execute=no_execution, check=check)
    old_bytes = old.read_bytes()
    data = json.loads(manifest.read_bytes())
    data["layout"]["routes"][0]["label"] = "Fiscal Q1 as reported"
    manifest.write_text(json.dumps(data))
    new = run_handoffs(manifest, state, execute=no_execution, check=check)
    assert new != old and old.read_bytes() == old_bytes
    assert len(list(state.glob("requests/*/*/*.response.md"))) == 3
    assert len(list(state.glob("completed-*.json"))) == 2


def test_every_retained_cell_and_paragraph_cites_exact_original_lines():
    raw = ANSWERS["CP-1B"].read_bytes()
    module, source, _ = literal_module("CP-1B", raw)
    lines = raw.decode().splitlines()
    for fact in module.facts:
        for citation in fact.citations:
            assert citation.quote == lines[int(citation.locator.split()[-1]) - 1]
            assert citation.source_sha256 == hashlib.sha256(raw).hexdigest()
    wrapped = next(f for f in module.facts if (f.text or "").startswith("No accepted budget"))
    assert len(wrapped.citations) > 1
    assert source.sha256 == hashlib.sha256(raw).hexdigest()


def test_literal_blank_zero_and_units_are_preserved_without_financial_reinterpretation():
    raw = b"""# CP-1B TDG
## Request
Retained synthetic boundary regression only.
## Sources
None.
## Findings
### Values
| Metric | Value | Unit |
|---|---|---|
| Zero | 0 | USD million |
| Missing | | USD/share |
## Calculations
None.
## Gaps
Missing remains missing.
## Next module
Delivery.
"""
    module, _, _ = literal_module("CP-1B", raw)
    row = {(f.label, f.field): f for f in module.facts if f.table_id.startswith("raw-")}
    assert row["Zero", "c0"].text == "0" and row["Zero", "c0"].status == "known"
    assert row["Missing", "c0"].text is None and row["Missing", "c0"].status == "missing"
    assert row["Missing", "c1"].text == "USD/share"


@pytest.mark.parametrize(
    "change,error",
    [
        (
            lambda d: d["layout"]["routes"][0].update(table_header="Nonexistent"),
            "markdown_selector",
        ),
        (lambda d: d["layout"]["routes"][0].update(table_header=None), "markdown_selector"),
        (
            lambda d: d["layout"]["routes"].append(d["layout"]["routes"][0].copy()),
            "markdown_selector",
        ),
        (lambda d: d["layout"]["routes"][0].update(prefix="1789"), "markdown_layout"),
        (lambda d: d["layout"]["routes"][0].update(block_id="variance-drivers"), "markdown_layout"),
        (lambda d: d["layout"]["blocks"].append("metric-strip"), "markdown_layout"),
    ],
)
def test_missing_ambiguous_duplicate_or_destructive_selector_refuses(tmp_path, change, error):
    data = json.loads((CASE / "workflow.json").read_bytes())
    direct = {
        "run": data["run"],
        "layout": data["layout"],
        "handoffs": {
            m: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for m, path in ANSWERS.items()
        },
    }
    change(direct)
    request = DeliveryRequest.model_validate_json(json.dumps(direct))
    path = tmp_path / "delivery.json"
    path.write_text(request.model_dump_json())
    with pytest.raises(ValueError, match=error):
        delivery_files(path)


def test_foreign_issuer_and_changed_handoff_refuse(tmp_path):
    manifest = job(tmp_path)
    data = json.loads(manifest.read_bytes())
    data["run"]["issuer_id"] = "OTHER"
    data["run"]["issuer_name"] = "Other issuer"
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="markdown_issuer"):
        replay_handoffs(manifest, tmp_path / "foreign")
    manifest = job(tmp_path)
    data = json.loads(manifest.read_bytes())
    data["retained_handoffs"]["CP-1B"]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="cpos_input_changed"):
        replay_handoffs(manifest, tmp_path / "changed")


def test_literal_delivery_does_not_relax_native_cp1b_layout(tmp_path):
    report = replay_handoffs(job(tmp_path), tmp_path / "state")
    view = View.model_validate_json((report.parent / "view.json").read_bytes())
    with pytest.raises(ValueError, match="CP1B layout requires exactly its three ordered tables"):
        _validate_cp1b_layout(next(m for m in view.modules if m.module_id == "CP-1B"))
