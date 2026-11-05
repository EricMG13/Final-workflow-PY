"""Offline publication checks against independently transcribed expectations.

These are retained live-handoff publications, not new provider execution.
"""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from deploy_vii.contracts import View
from deploy_vii.report_view import ReportView, pathways
from deploy_workflow.handoff_delivery import HandoffInput, verify_delivery
from deploy_workflow.owners.cpos import _comparison_bundle

BASE = Path(__file__).resolve().parent


def verify(name):
    case = BASE / name
    manifest = json.loads((case / "delivery.json").read_bytes())
    report = verify_delivery(case / "delivery.json", case / "published")
    view = View.model_validate_json((report.parent / "view.json").read_bytes())
    rv = ReportView.model_validate_json((report.parent / "report-view.json").read_bytes())
    assert tuple(b.block_id for b in rv.blocks) == next(
        p.blocks for p in pathways() if p.id == name
    )
    assert all(b.state == "populated" for b in rv.blocks)
    for module, spec in manifest["handoffs"].items():
        raw = (case / spec["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == spec["sha256"]
        assert (report.parent / (module + ".md")).read_bytes() == raw
        lines = raw.decode().splitlines()
        current = next(m for m in view.modules if m.module_id == module)
        assert current.artifact_sha256 == spec["sha256"]
        for fact in current.facts:
            for citation in fact.citations:
                assert citation.source_sha256 == spec["sha256"]
                assert lines[int(citation.locator.split()[-1]) - 1] == citation.quote
    receipt = report.parent / "delivery.json"
    _comparison_bundle(
        report.parent,
        HandoffInput(path=receipt.name, sha256=hashlib.sha256(receipt.read_bytes()).hexdigest()),
    )
    if name == "relative_value":
        fig = next(b for b in rv.blocks if b.block_id == "yield-against-maturity").figures[0]
        assert [m.value for m in fig.chart.marks] == list(
            map(Decimal, ["0.056003", "0.061317", "0.056224", "0.063169"])
        )
        assert fig.chart.unit_class == "percent" and len(fig.chart.table_twin.rows) == 4
    if name == "portfolio_decision":
        assert rv.call[0].value_text == "Requires More Work"
        assert b"30823830378.19" in (report.parent / "CP-3.md").read_bytes()
        assert b"13509200" in (report.parent / "CP-3.md").read_bytes()
    if name == "earnings_update":
        figures = next(b for b in rv.blocks if b.block_id == "metric-strip").figures
        assert [m.value for m in figures[2].chart.marks] == list(map(Decimal, [3001, 3472, 6261]))
        calc = json.loads((report.parent / "calculation.json").read_bytes())["values"]
        assert calc["FY2024"]["issuer_ordinary_ebitda"]["amount"] == "3813"
        assert calc["FY2024"]["issuer_as_defined"]["amount"] == "4173"
        assert View.model_validate_json(
            (report.parent / "model-view.json").read_bytes()
        ).modules == tuple(m for m in view.modules if m.module_id == "CP-MODEL")
    if name == "covenant_refinancing":
        figure = next(b for b in rv.blocks if b.block_id == "maturity-wall").figures[0]
        assert [m.value for m in figure.chart.marks] == list(
            map(Decimal, [93, 92, 92, 6637, 4768, 12637])
        )
        assert "conflict" in figure.title and "2,650" in figure.title
    if name == "distressed_restructuring":
        assert "Actual distress is not established" in manifest["layout"]["scope"]
        assert (
            "no quantified recovery"
            in next(b for b in rv.blocks if b.block_id == "recovery-by-class").note
        )
        assert (
            "no realizable-value allocation"
            in next(b for b in rv.blocks if b.block_id == "value-allocation-claims").note
        )
    return {
        "report": str(report.relative_to(BASE.parent)),
        "panels": len(rv.blocks),
        "scope": manifest["layout"]["scope"],
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "handoff_hashes": {m: v["sha256"] for m, v in manifest["handoffs"].items()},
        "verification": "Exact preset panelset, populated blocks, immutable handoff byte parity, every fact citation/physical line/sourcehash, complete CP8-ready bundle verified; chart/Model/portfolio independent expected values checked where applicable.",
    }


if __name__ == "__main__":
    for name in [
        "earnings_update",
        "relative_value",
        "portfolio_decision",
        "distressed_restructuring",
        "covenant_refinancing",
    ]:
        if (BASE / name / "published").exists():
            print(name, verify(name)["panels"], "panels verified")
