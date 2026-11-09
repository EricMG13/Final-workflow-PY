"""Actual portfolio handoffs; publication replay is not fresh underwriting."""

import hashlib
import json
from pathlib import Path

import pytest

from deploy_vii.report_view import pathways
from deploy_workflow.handoff_delivery import DeliveryRequest
from deploy_workflow.markdown_delivery import _portfolio_call, literal_module, markdown_files
from deploy_workflow.owners.cpos import run_handoffs

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "runs/cpos-lqd-portfolio-001"


def test_all_portfolio_sections_and_actual_cited_posture_without_execution(tmp_path):
    data = json.loads((CASE / "workflow.json").read_bytes())
    for group in ("sources", "instructions", "retained_handoffs"):
        for spec in data[group].values():
            spec["path"] = str((CASE / spec["path"]).resolve())
    manifest = tmp_path / "workflow.json"
    manifest.write_text(json.dumps(data))
    expected = {m: Path(spec["path"]).read_bytes() for m, spec in data["retained_handoffs"].items()}

    def no_execute(task):
        raise AssertionError("Delivery must not rerun analysis")

    def check(task, raw):
        assert raw == expected[task.module_id]
        return ()

    report = run_handoffs(manifest, tmp_path / "state", execute=no_execute, check=check)
    view = json.loads((report.parent / "view.json").read_bytes())
    rv = json.loads((report.parent / "report-view.json").read_bytes())
    preset = next(p for p in pathways() if p.id == "portfolio_decision")
    assert tuple(b["block_id"] for b in rv["blocks"]) == preset.blocks
    assert all(b["state"] == "populated" for b in rv["blocks"])
    assert len(rv["call"]) == 1
    call = rv["call"][0]
    assert (call["label"], call["value_text"]) == ("Portfolio posture", "Requires More Work")
    assert call["meter"] is None and call["direction"] is None
    assert rv["call_withheld"] is None
    passport = next(p for p in rv["passports"] if p["ref_id"] == call["ref_id"])
    fields = {f["name"]: f["value"] for f in passport["fields"]}
    assert fields["Source"] == "CP-6"
    assert fields["SHA-256"] == hashlib.sha256(expected["CP-6"]).hexdigest()
    assert "Final Sizing Posture: Requires More Work" in fields["Quote"]
    assert [m["module_id"] for m in view["modules"]] == ["CP-3", "CP-6", "CP-5"]
    assert run_handoffs(manifest, tmp_path / "state", execute=no_execute, check=check) == report
    assert len(list((tmp_path / "state/requests").glob("*/*/*.response.md"))) == 3


def posture_input(text, *, heading="Final Sizing Posture", module_id="CP-6"):
    raw = (
        f"# {module_id} — LQD\n\n## Request\n\nSynthetic posture transport test.\n\n"
        f"## Sources\n\nSynthetic test only.\n\n## Findings\n\n### {heading}\n\n{text}\n\n"
        "## Calculations\n\nNone.\n\n## Gaps\n\nNo issuer proof.\n\n"
        "## Next module\n\nTransport verification.\n"
    ).encode()
    module, _, metadata = literal_module(module_id, raw)
    refs = {(module_id, fact.fact_id): ("C1",) for fact in module.facts}
    return module, metadata, refs


@pytest.mark.parametrize(
    "posture",
    ["Include", "Avoid", "Resize-Reduce", "Resize-Increase", "Maintain-Hold", "Requires More Work"],
)
def test_copy_only_the_explicit_terminal_posture_without_scoring(posture):
    result = _portfolio_call(
        *posture_input(f"**Final Sizing Posture: {posture}.** Source rationale.")
    )
    assert result.value_text == posture and result.ref_id == "C1"
    assert result.meter is None and result.direction is None


@pytest.mark.parametrize(
    "text",
    [
        "Final Sizing Posture: Include if new evidence arrives.",
        "Final Sizing Posture: Strong Include.",
        "Final Sizing Posture: Requires More Workish.",
        "Final Sizing Posture:",
        "Final Sizing Posture: Avoid.\n\nFinal Sizing Posture: Include.",
        "Final Sizing Posture: Avoid.\n\nFinal Sizing Posture: Avoid.",
    ],
)
def test_unsupported_or_ambiguous_source_record_cannot_make_a_header(text):
    with pytest.raises(ValueError, match="markdown_posture"):
        _portfolio_call(*posture_input(text))


def test_no_foreign_heading_owner_or_absent_record_becomes_a_posture():
    assert _portfolio_call(None, {}, {}) is None
    assert _portfolio_call(*posture_input("An assessment remains incomplete.")) is None
    assert (
        _portfolio_call(*posture_input("Final Sizing Posture: Include.", heading="Example")) is None
    )
    assert (
        _portfolio_call(*posture_input("Final Sizing Posture: Include.", module_id="CP-3")) is None
    )


def test_terminal_posture_requires_a_source_reference():
    module, metadata, _ = posture_input("Final Sizing Posture: Requires More Work.")
    with pytest.raises(ValueError, match="markdown_posture"):
        _portfolio_call(module, metadata, {})


@pytest.mark.parametrize(
    "posture",
    [
        "Avoid",
        "Watchlist",
        "Starter Position",
        "Core Hold",
        "Add / Increase",
        "Reduce / Trim",
        "Exit",
        "Requires More Work",
    ],
)
def test_base_committee_action_is_copied_without_portfolio_translation(posture):
    inputs = posture_input(
        f"**Final Action Bias: {posture}.** Historical issuer case only.",
        heading="Action Bias Determination",
    )
    result = _portfolio_call(*inputs, portfolio=False)
    assert (result.label, result.value_text, result.ref_id) == ("Action bias", posture, "C1")
    assert result.meter is None and result.direction is None
    assert _portfolio_call(*inputs) is None


@pytest.mark.parametrize(
    "text",
    [
        "Final Action Bias: Watchlist if evidence arrives.",
        "Final Action Bias: Watchlistish.",
        "Final Action Bias: Include.",
        "Final Action Bias: Watchlist.\n\nFinal Action Bias: Avoid.",
    ],
)
def test_base_committee_conditional_unknown_or_conflicting_action_is_refused(text):
    with pytest.raises(ValueError, match="markdown_posture"):
        _portfolio_call(*posture_input(text, heading="Action Bias Determination"), portfolio=False)


def test_actual_tdg_action_reaches_header_with_exact_source_trace():
    import hashlib

    from deploy_workflow.handoff_delivery import delivery_files

    manifest = ROOT / "runs/cpos-sol-remaining-20261105/pathways/earnings_update/delivery.json"
    files = delivery_files(manifest)
    report = json.loads(files["report-view.json"])
    call = report["call"][0]
    assert (call["label"], call["value_text"]) == ("Action bias", "Watchlist")
    assert report["call_withheld"] is None
    view = json.loads(files["view.json"])
    module = next(m for m in view["modules"] if m["module_id"] == "CP-6")
    fact = next(
        f for f in module["facts"] if (f.get("text") or "").startswith("Final Action Bias:")
    )
    citation = fact["citations"][0]
    raw = files["CP-6.md"]
    assert citation["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert raw.decode().splitlines()[int(citation["locator"].split()[-1]) - 1] == citation["quote"]


def test_other_pathway_keeps_its_existing_header_contract():
    data = json.loads((CASE / "workflow.json").read_bytes())
    request = DeliveryRequest.model_validate_json(
        json.dumps(
            {
                "run": {**data["run"], "pathway": "credit_snapshot"},
                "handoffs": {
                    "CP-6": {
                        key: data["retained_handoffs"]["CP-6"][key] for key in ("path", "sha256")
                    }
                },
                "layout": {
                    "blocks": ["key-findings"],
                    "routes": [
                        {
                            "module_id": "CP-6",
                            "heading": "Final Sizing Posture",
                            "kind": "prose",
                            "block_id": "key-findings",
                        }
                    ],
                    "scope": "Synthetic transport check over an actual handoff; not new analysis.",
                },
            }
        )
    )
    files = markdown_files(request, CASE)
    rv = json.loads(files["report-view.json"])
    assert rv["call"][0]["value_text"] == "Assessment pending"


def repeated_posture_input(first, second):
    """`### Final Sizing Posture` once under Findings and once under Gaps (a repeated heading)."""
    raw = (
        "# CP-6 — LQD\n\n## Request\n\nSynthetic posture transport test.\n\n"
        "## Sources\n\nSynthetic test only.\n\n## Findings\n\n### Final Sizing Posture\n\n"
        f"{first}\n\n## Calculations\n\nNone.\n\n## Gaps\n\n### Final Sizing Posture\n\n"
        f"{second}\n\n## Next module\n\nTransport verification.\n"
    ).encode()
    module, _, metadata = literal_module("CP-6", raw)
    return module, metadata, {("CP-6", fact.fact_id): ("C1",) for fact in module.facts}


def test_a_posture_under_a_repeated_heading_is_still_found_once():
    # Hand-derived: the repeated heading gives path labels ("Findings > Final Sizing Posture",
    # "Gaps > Final Sizing Posture"); the one terminal record is still the header's posture.
    result = _portfolio_call(
        *repeated_posture_input("Final Sizing Posture: Include.", "Not reassessed here.")
    )
    assert (result.value_text, result.ref_id) == ("Include", "C1")


def test_conflicting_postures_under_a_repeated_heading_are_refused_not_withheld():
    with pytest.raises(ValueError, match="markdown_posture"):
        _portfolio_call(
            *repeated_posture_input(
                "Final Sizing Posture: Avoid.", "Final Sizing Posture: Include."
            )
        )
