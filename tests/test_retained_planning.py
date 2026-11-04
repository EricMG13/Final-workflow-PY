"""Retained inputs bound execution; default native requirements and checks still apply."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from deploy_vii import registry
from deploy_vii.report_view import ReportView
from deploy_workflow.handoff_delivery import DeliveryRequest, delivery_files
from deploy_workflow.owners.cpos import replay_handoffs, run_handoffs

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "runs/cpos-ford-ratings-2024-001"
ORDER = ("CP-0", "CP-1", "CP-2G", "CP-2H")


def job(tmp_path):
    data = json.loads((CASE / "workflow.json").read_bytes())
    for group in ("sources", "instructions", "retained_handoffs"):
        for spec in data[group].values():
            spec["path"] = str((CASE / spec["path"]).resolve())
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(data))
    return path


def test_published_forecast_boundary_preserves_fresh_requirements_and_input_graph():
    retained = {"CP-2G": ["CP-0", "CP-1"]}
    before = copy.deepcopy(retained)
    assert registry.plan(("CP-2H",), retained=retained) == ORDER
    assert retained == before
    assert registry.plan(("CP-2H",)) == ("CP-0", "CP-1", "CP-2A", "CP-2G", "CP-2H")
    assert registry.plan(("CP-2H",), retained={"CP-0": (), "CP-1": ("CP-0",)}) == (
        "CP-0",
        "CP-1",
        "CP-2A",
        "CP-2G",
        "CP-2H",
    )


@pytest.mark.parametrize(
    "retained", [{"UNKNOWN": ()}, {"CP-2G": ("UNKNOWN",)}, {"CP-2F": ()}, {"CP-2G": ("CP-2F",)}]
)
def test_retained_context_ids_must_be_known_canonical_ids(retained):
    with pytest.raises(ValueError, match="Unknown canonical retained"):
        registry.plan(("CP-2H",), retained=retained)


def test_retained_cycles_fail_and_quality_review_still_follows_every_selected_analyst():
    with pytest.raises(ValueError, match="cyclic selected"):
        registry.plan(("CP-2G",), retained={"CP-1": ("CP-2G",)})
    graph = registry.dependencies(
        ("CP-2H", "CP-5A"), retained={"CP-2G": ("CP-0", "CP-1"), "CP-5": ("CP-0",)}
    )
    assert {"CP-1", "CP-2G", "CP-2H"} <= graph["CP-5"]


def test_actual_ford_handoffs_deliver_without_a_new_stress_or_model_call(tmp_path):
    path = job(tmp_path)
    state = tmp_path / "state"
    checked = []
    data = json.loads(path.read_bytes())

    def no_execution(task):
        pytest.fail(f"Already checked handoff re-executed: {task.module_id}")

    def check(task, raw):
        assert list(task.handoffs) == list(ORDER[: len(checked)])
        assert (
            hashlib.sha256(raw).hexdigest() == data["retained_handoffs"][task.module_id]["sha256"]
        )
        checked.append(task.module_id)
        return ()

    report = run_handoffs(path, state, execute=no_execution, check=check)
    assert checked == list(ORDER)
    assert not (state / "requests/CP-2A").exists()
    rv = ReportView.model_validate_json((report.parent / "report-view.json").read_bytes())
    assert rv.pathway.title == "Ford Otosan · historical ratings review"
    assert "April 2024" in rv.pathway.question
    assert rv.blocks[0].block_id == "rating-triggers"
    assert len(rv.blocks[0].rows) == 2 and len(rv.blocks[0].tabs) == 10
    values = [c.text for r in rv.blocks[0].rows for c in r.cells]
    assert "BB- preliminary, Positive" in values and "BB+(EXP), RR4" in values
    assert replay_handoffs(path, state) == report
    assert len(list(state.glob("requests/*/*/*.response.md"))) == 4
    assert not list(report.parent.glob("*.xlsx"))


def test_reuse_planning_does_not_weaken_source_or_consumed_input_hash_checks(tmp_path):
    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data["retained_handoffs"]["CP-2G"]["upstream"]["CP-1"] = "0" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="cpos_retained_stale: CP-2G"):
        replay_handoffs(path, tmp_path / "state")
    assert not (tmp_path / "state/requests/CP-2G").exists()
    assert not (tmp_path / "state/deliveries").exists()


def direct_delivery(tmp_path):
    data = json.loads(job(tmp_path).read_bytes())
    return {
        "run": data["run"],
        "layout": data["layout"],
        "handoffs": {
            module: {"path": spec["path"], "sha256": spec["sha256"]}
            for module, spec in data["retained_handoffs"].items()
        },
    }


@pytest.mark.parametrize(
    "field,value",
    [("issuer_aliases", [""]), ("issuer_aliases", [" \t"]), ("title", " "), ("question", "")],
)
def test_blank_identity_aliases_and_report_headings_refuse(tmp_path, field, value):
    data = direct_delivery(tmp_path)
    data["layout"][field] = value
    with pytest.raises(ValueError):
        DeliveryRequest.model_validate_json(json.dumps(data))


def test_an_issuer_named_only_in_sources_cannot_supply_a_generic_declaration(tmp_path):
    data = direct_delivery(tmp_path)
    spec = data["handoffs"]["CP-1"]
    raw = Path(spec["path"]).read_text()
    declaration, remaining = raw.split("## Sources", 1)
    declaration = declaration.replace("Ford Otomotiv Sanayi A.S.", "Unrelated issuer")
    changed = (
        declaration
        + "## Sources\nFord Otomotiv Sanayi A.S. is mentioned only as a reference.\n"
        + remaining
    )
    path = tmp_path / "unrelated.md"
    path.write_text(changed)
    spec.update(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    manifest = tmp_path / "delivery.json"
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="markdown_issuer"):
        delivery_files(manifest)


@pytest.mark.parametrize("separator", ["\n", "  ", "\t", "\u00a0"])
def test_wrapped_issuer_declaration_keeps_original_handoff_bytes(tmp_path, separator):
    data = direct_delivery(tmp_path)
    spec = data["handoffs"]["CP-1"]
    original = Path(spec["path"]).read_text()
    declaration, remaining = original.split("## Sources", 1)
    wrapped = declaration.replace("Ford Otomotiv Sanayi A.S.", "Ford" + separator + "Otosan")
    raw = (wrapped + "## Sources" + remaining).encode()
    path = tmp_path / "wrapped.md"
    path.write_bytes(raw)
    spec.update(path=str(path), sha256=hashlib.sha256(raw).hexdigest())
    manifest = tmp_path / "delivery.json"
    manifest.write_text(json.dumps(data))
    files = delivery_files(manifest)
    assert files["CP-1.md"] == raw
    view = json.loads(files["view.json"])
    module = next(m for m in view["modules"] if m["module_id"] == "CP-1")
    assert module["artifact_sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("alias", ["Ford\nOtosan", "Ford  Otosan"])
def test_alias_whitespace_does_not_change_the_issuer_identity(tmp_path, alias):
    data = direct_delivery(tmp_path)
    data["layout"]["issuer_aliases"] = [alias]
    # CP-0's Request contains the same brand identity in ordinary source text.
    data["handoffs"] = {"CP-0": data["handoffs"]["CP-0"]}
    data["layout"]["routes"] = [
        {
            "module_id": "CP-0",
            "heading": "Findings",
            "kind": "prose",
            "block_id": "rating-triggers",
            "label": "Historical intake",
        }
    ]
    # Require the brand alias: the legal name/id is intentionally absent here.
    data["run"].update(issuer_name="Unused legal label", issuer_id="UNUSED-ID")
    manifest = tmp_path / "delivery.json"
    manifest.write_text(json.dumps(data))
    assert "report.html" in delivery_files(manifest)


def test_issuer_identity_cannot_be_assembled_across_title_and_request(tmp_path):
    data = direct_delivery(tmp_path)
    spec = data["handoffs"]["CP-1"]
    _, remaining = Path(spec["path"]).read_text().split("## Sources", 1)
    declaration = "# CP-1 — Ford\n\n## Request\n\nOtosan is a source for an unrelated case.\n\n"
    raw = (declaration + "## Sources" + remaining).encode()
    path = tmp_path / "different-declarations.md"
    path.write_bytes(raw)
    spec.update(path=str(path), sha256=hashlib.sha256(raw).hexdigest())
    manifest = tmp_path / "delivery.json"
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="markdown_issuer"):
        delivery_files(manifest)
