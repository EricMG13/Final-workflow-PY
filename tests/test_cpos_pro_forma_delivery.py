"""Task 11b: the Primary pro forma tables are delivered in the `pro-forma` report block. Handoffs
are synthetic (frozen key cases from tests/fixtures/primary-pro-forma/checker-cases.json), not
model runs. Expected cells are read from the handoff text; the golden digests were computed from
the Task 11a tree (7f6a39dd) before the layout change."""

import hashlib
import itertools
import json
from datetime import date
from pathlib import Path

import pytest
from test_delivery_low_s04 import RUN, handoff

from deploy_vii.contracts import PATHWAY_MODULES, Run
from deploy_vii.report_view import ReportView, pathways
from deploy_workflow.handoff_delivery import DeliveryRequest, HandoffInput
from deploy_workflow.markdown_delivery import markdown_files
from deploy_workflow.owners.cpos_launch import LaunchRefused, _layout

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    c["id"]: c
    for c in json.loads((ROOT / "tests/fixtures/primary-pro-forma/checker-cases.json").read_text())[
        "cases"
    ]
}
HEAD = (
    "# CP-2 Acme Corp\n\n## Request\nAcme Corp pro forma.\n\n## Sources\nsrc.pdf\n\n## Findings\n\n"
)
PROSE = "### Key findings\n\nLeverage rises.\n\n### Strengths and weaknesses\n\nScale.\n\n"
TAIL = "## Calculations\nNone.\n\n## Gaps\nNone.\n\n## Next module\nDelivery.\n"
CP2_RUN = RUN.model_copy(update={"requested_modules": ("CP-2",)})
# sha256 over the sorted (key, layout digest) of every case the change must leave alone.
UNCHANGED_LAYOUTS = "04c567a99c8435127147c69aebf94b37f09976019194eafbc59e7592da9074ab"
UNCHANGED_DELIVERY = {
    "secondary-cp2": "6429866a739ff110ca30e7cc40eb82496d30293f753f2d90544efc002872f4d5",
    "primary-cp1": "aec2f4ce43b3554a63c69a9086c6dcee14efef390979fed0624ba944fa70d1ef",
}


def layout_digests() -> dict[str, str]:
    out = {}
    for pathway in pathways():
        full = tuple(PATHWAY_MODULES.get(pathway.id, ()))
        sets = {"all": full, "no-cp2": tuple(m for m in full if m != "CP-2"), "cp2": ("CP-2",)}
        for (name, ordered), run_type, legal in itertools.product(
            sets.items(), ("primary", "secondary", "research"), ("executed", "draft")
        ):
            if not ordered:
                continue
            run = Run(
                run_id="x",
                issuer_id="i",
                issuer_name="Issuer",
                as_of=date(2026, 1, 1),
                case_kind="public",
                pathway=pathway.id,
                requested_modules=ordered,
            )
            try:
                layout, omitted = _layout(
                    run, ordered, ("Iss",), "cfg", run_type=run_type, legal_documents=legal
                )
                text = layout.model_dump_json() + "|" + ",".join(omitted)
            except LaunchRefused as refusal:  # A refusal is part of the layout's behaviour.
                text = f"ERR LaunchRefused{refusal}"
            out[f"{pathway.id}/{name}/{run_type}/{legal}"] = hashlib.sha256(
                text.encode()
            ).hexdigest()
    return out


def unchanged(key: str) -> bool:
    pathway, name, run_type, _ = key.split("/")
    return not (pathway == "credit_snapshot" and name != "no-cp2" and run_type == "primary")


def deliver(tmp_path: Path, run: Run, module: str, text: str, run_type: str):
    raw = text.encode()
    layout, _ = _layout(run, (module,), (), "cfg", run_type=run_type, legal_documents="executed")
    (tmp_path / f"{module}.md").write_bytes(raw)
    spec = HandoffInput(path=f"{module}.md", sha256=hashlib.sha256(raw).hexdigest())
    return markdown_files(
        DeliveryRequest(run=run, handoffs={module: spec}, layout=layout), tmp_path
    )


def cp2_handoff(case_id: str) -> str:
    return HEAD + PROSE + CASES[case_id]["findings"] + "\n\n" + TAIL


def table_cells(findings: str, heading: str) -> list[list[str]]:
    """Rows of the table under `### heading`, from the handoff text (header, rule dropped)."""
    section = findings.split(f"### {heading}\n", 1)[1].split("\n### ", 1)[0]
    rows = [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in section.splitlines()
        if line.startswith("|")
    ]
    return rows[2:]


def test_layout_adds_the_two_routes_on_primary_with_cp2_only():
    primary, _ = _layout(CP2_RUN, ("CP-2",), (), "cfg", run_type="primary", legal_documents="draft")
    routes = [r for r in primary.routes if r.block_id == "pro-forma"]
    assert [(r.module_id, r.kind, r.heading, r.table_header) for r in routes] == [
        (
            "CP-2",
            "table",
            "Pro forma capitalisation",
            "Instrument",
        ),
        (
            "CP-2",
            "table",
            "Pro forma leverage",
            "Basis",
        ),
    ]
    assert "pro-forma" in primary.blocks
    assert "transaction-summary" not in primary.blocks  # CP-1A is absent: no prose route for it


def test_layout_is_unchanged_outside_primary_with_cp2():
    digests = layout_digests()
    kept = sorted((k, v) for k, v in digests.items() if unchanged(k))
    assert len(kept) == 104
    assert hashlib.sha256(json.dumps(kept).encode()).hexdigest() == UNCHANGED_LAYOUTS


@pytest.mark.parametrize(
    "case_id",
    [
        "cp2-full-valid",
        "cap-usd-eur-per-currency-totals",
        "leverage-private-deal-reported-not-supplied",
    ],
)
def test_pro_forma_tables_reach_the_report_unchanged(tmp_path, case_id):
    """Synthetic handoff (frozen key case), not a model run."""
    text = cp2_handoff(case_id)
    files = deliver(tmp_path, CP2_RUN, "CP-2", text, "primary")
    report = ReportView.model_validate_json(files["report-view.json"])
    block = next(b for b in report.blocks if b.block_id == "pro-forma")
    assert block.kind == "dense"
    assert block.title == "Pro forma capitalisation and leverage"
    assert [t.label for t in block.tabs] == ["Pro forma leverage — Basis"]
    assert block.tab_label == "Pro forma capitalisation — Instrument"
    findings = CASES[case_id]["findings"]
    for heading, table in (
        ("Pro forma capitalisation", block),
        ("Pro forma leverage", block.tabs[0]),
    ):
        want = table_cells(findings, heading)
        got = [[r.label, *(c.text for c in r.cells)] for r in table.rows]
        assert got == want
    assert all(c.text.strip() for r in block.rows for c in r.cells)  # nothing blank
    assert "register" not in json.dumps(json.loads(files["report-view.json"])["blocks"]).lower()


def test_not_supplied_cells_stay_text(tmp_path):
    """Synthetic handoff (frozen key case), not a model run."""
    files = deliver(tmp_path, CP2_RUN, "CP-2", cp2_handoff("cp2-full-valid"), "primary")
    report = ReportView.model_validate_json(files["report-view.json"])
    block = next(b for b in report.blocks if b.block_id == "pro-forma")
    cash = next(r for r in block.rows if r.label == "Cash")
    assert "Not supplied: not stated" in [c.text for c in cash.cells]


def test_missing_table_fails_with_the_selector_error(tmp_path):
    text = HEAD + PROSE + TAIL
    with pytest.raises(ValueError, match="markdown_selector: expected one CP-2/Pro forma capital"):
        deliver(tmp_path, CP2_RUN, "CP-2", text, "primary")


def test_secondary_delivery_is_byte_identical_to_the_old_tree(tmp_path):
    text = cp2_handoff("cp2-full-valid")
    files = deliver(tmp_path, CP2_RUN, "CP-2", text, "secondary")
    assert "pro-forma" not in json.loads(files["report-view.json"])["blocks"].__repr__()
    got = hashlib.sha256(
        json.dumps({k: hashlib.sha256(v).hexdigest() for k, v in sorted(files.items())}).encode()
    ).hexdigest()
    assert got == UNCHANGED_DELIVERY["secondary-cp2"]


def test_primary_without_cp2_delivery_is_byte_identical_to_the_old_tree(tmp_path):
    files = deliver(tmp_path, RUN, "CP-1", handoff(), "primary")
    got = hashlib.sha256(
        json.dumps({k: hashlib.sha256(v).hexdigest() for k, v in sorted(files.items())}).encode()
    ).hexdigest()
    assert got == UNCHANGED_DELIVERY["primary-cp1"]
