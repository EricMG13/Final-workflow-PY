"""Task 11b: the Primary pro forma tables are delivered in the `pro-forma` report block. Handoffs
are synthetic (frozen key cases from tests/fixtures/primary-pro-forma/checker-cases.json), not
model runs. Expected cells are read from the handoff text; the golden digests were computed from
the Task 11a tree (7f6a39dd) before the layout change."""

import hashlib
import itertools
import json
from datetime import date
from html import escape
from pathlib import Path

import pytest
from test_delivery_low_s04 import RUN, handoff

from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import PATHWAY_MODULES, Run, View
from deploy_vii.render import render
from deploy_vii.report_view import ReportView, build, pathways
from deploy_workflow.handoff_delivery import DeliveryRequest, HandoffInput
from deploy_workflow.markdown_delivery import markdown_files
from deploy_workflow.owners.cpos_launch import REGISTER_HEADER, LaunchRefused, _layout

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


RC2_DIR = ROOT / "tests/fixtures/primary-pro-forma/rc2"
SU_TAB = json.loads((RC2_DIR / "delivered-block-rc2.json").read_text())["sources_and_uses"]
PAIR_NOTE = json.loads((RC2_DIR / "delivered-notes.json").read_text())["cases"][
    "fake_cp2_full_valid_plus_cp1a_valid"
]["expected_block_note"]
PAIR_RUN = RUN.model_copy(update={"requested_modules": ("CP-1A", "CP-2")})
SU_KEY_CASE = "cp1a-sources-uses-valid-user-entered"


def test_layout_adds_sources_and_uses_as_a_third_route_when_cp1a_and_cp2_both_run():
    """R-C2-2: CP-1A's table is a further tab of the pro-forma block, after the leverage tab."""
    layout, _ = _layout(
        PAIR_RUN, ("CP-1A", "CP-2"), (), "cfg", run_type="primary", legal_documents="executed"
    )
    routes = [r for r in layout.routes if r.block_id == "pro-forma"]
    assert [(r.module_id, r.kind, r.heading, r.table_header) for r in routes] == [
        ("CP-2", "table", "Pro forma capitalisation", "Instrument"),
        ("CP-2", "table", "Pro forma leverage", "Basis"),
        ("CP-1A", "table", "Sources and uses", "Side"),
    ]
    assert layout.blocks.count("pro-forma") == 1


@pytest.mark.parametrize(
    ("ordered", "run_type"),
    [(("CP-1A",), "primary"), (("CP-1A", "CP-2"), "secondary"), (("CP-2",), "primary")],
)
def test_no_sources_and_uses_route_unless_primary_runs_both_modules(ordered, run_type):
    """Controller rulings u10/u11: CP-1A alone is not routed (a known limit)."""
    run = RUN.model_copy(update={"requested_modules": ordered})
    layout, _ = _layout(run, ordered, (), "cfg", run_type=run_type, legal_documents="executed")
    assert not [r for r in layout.routes if r.heading == "Sources and uses"]


def stub(route) -> str:
    body = "Prose text.\n\n" if route.kind == "prose" else "| A | B |\n| --- | --- |\n| x | 1 |\n\n"
    return f"### {route.heading}\n\n{body}"


def layout_of_pair():
    layout, _ = _layout(
        PAIR_RUN, ("CP-1A", "CP-2"), (), "cfg", run_type="primary", legal_documents="executed"
    )
    return layout


def deliver_texts(tmp_path: Path, texts: dict[str, str]):
    """Whole handoffs of the CP-1A and CP-2 Primary run through the app's layout and delivery."""
    specs = {}
    for module, text in texts.items():
        raw = text.encode()
        (tmp_path / f"{module}.md").write_bytes(raw)
        specs[module] = HandoffInput(path=f"{module}.md", sha256=hashlib.sha256(raw).hexdigest())
    request = DeliveryRequest(run=PAIR_RUN, handoffs=specs, layout=layout_of_pair())
    return markdown_files(request, tmp_path)


def deliver_pair(tmp_path: Path, findings: dict[str, str]):
    """Routes under test carry the given findings; every other routed heading carries a stub."""
    texts = {}
    for module in ("CP-1A", "CP-2"):
        routed = [
            r
            for r in layout_of_pair().routes
            if r.module_id == module and r.block_id != "pro-forma"
        ]
        body = "".join(stub(r) for r in routed) + findings[module] + "\n\n"
        texts[module] = (
            f"# {module} Acme Corp\n\n## Request\nAcme Corp pro forma.\n\n## Sources\nsrc.pdf\n\n"
            f"## Findings\n\n{body}{TAIL}"
        )
    return deliver_texts(tmp_path, texts)


def pair_block(tmp_path: Path):
    files = deliver_pair(
        tmp_path,
        {
            "CP-1A": CASES[SU_KEY_CASE]["findings"],
            "CP-2": CASES["cp2-full-valid"]["findings"],
        },
    )
    report = ReportView.model_validate_json(files["report-view.json"])
    return next(b for b in report.blocks if b.block_id == "pro-forma")


def test_sources_and_uses_is_a_tab_after_leverage_with_the_handoffs_cells(tmp_path):
    """R-C2-2 (key rc2/delivered-block-rc2.json): primary = capitalisation, then the leverage tab,
    then Sources and uses; the capitalisation and leverage cells are the unchanged key's."""
    block = pair_block(tmp_path)
    delivered = json.loads(
        (ROOT / "tests/fixtures/primary-pro-forma/delivered-block.json").read_text()
    )["pro-forma"]
    assert [t.label for t in block.tabs] == ["Pro forma leverage — Basis", SU_TAB["label"]]
    assert block.tab_label == "Pro forma capitalisation — Instrument"
    for table, key in (
        (block, delivered["capitalisation"]),
        (block.tabs[0], delivered["leverage"]),
        (block.tabs[1], SU_TAB),
    ):
        assert [table.row_header, *table.columns] == key["header"]
        assert [[r.label, *(c.text for c in r.cells)] for r in table.rows] == key["rows"]
    assert block.full_analysis_route == "CP-2"


def test_the_block_note_names_each_table_and_asserts_no_other_tables_unit(tmp_path):
    """R-C2-5 (key rc2/delivered-notes.json, rulings n1 to n6)."""
    assert pair_block(tmp_path).note == PAIR_NOTE


def test_a_unit_sentence_stays_with_its_own_table(tmp_path):
    """The unit sentence of the sources-and-uses prose is prefixed with that table's name, and the
    capitalisation prose is not read as a unit for it (rulings n1, n5)."""
    findings = CASES[SU_KEY_CASE]["findings"].replace(
        "### Sources and uses\n",
        "### Sources and uses\n\nAmounts are **USD millions** throughout.\n",
    )
    files = deliver_pair(tmp_path, {"CP-1A": findings, "CP-2": CASES["cp2-full-valid"]["findings"]})
    report = ReportView.model_validate_json(files["report-view.json"])
    note = next(b for b in report.blocks if b.block_id == "pro-forma").note
    assert note is not None
    assert note.endswith(" · Sources and uses: Amounts are USD millions throughout.")
    assert note.count("USD millions") == 1


REGISTER = (
    f"### Legal document register\n\n| {' | '.join(REGISTER_HEADER)} |\n"
    f"| {' | '.join(['---'] * len(REGISTER_HEADER))} |\n"
    "| REGISTER-MARKER-7 indenture | credit agreement or indenture | draft | 1 | src.pdf |\n\n"
)


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
    findings = CASES[case_id]["findings"]
    text = HEAD + PROSE + REGISTER + findings + "\n\n" + TAIL
    assert "REGISTER-MARKER-7" in text
    files = deliver(tmp_path, CP2_RUN, "CP-2", text, "primary")
    report = ReportView.model_validate_json(files["report-view.json"])
    block = next(b for b in report.blocks if b.block_id == "pro-forma")
    assert block.kind == "dense"
    assert block.title == "Pro forma capitalisation and leverage"
    assert [t.label for t in block.tabs] == ["Pro forma leverage — Basis"]
    assert block.tab_label == "Pro forma capitalisation — Instrument"
    for heading, table in (
        ("Pro forma capitalisation", block),
        ("Pro forma leverage", block.tabs[0]),
    ):
        want = table_cells(findings, heading)
        got = [[r.label, *(c.text for c in r.cells)] for r in table.rows]
        assert got == want
        assert all(cell.strip() for row in got for cell in row)  # nothing blank, either table
    # The handoff's balance-sheet date and LTM period survive exactly in the block note.
    lines = [l for l in findings.splitlines() if l.startswith(("Balance-sheet date:", "LTM"))]
    assert len(lines) == 2
    # R-C2-5: each table's prose carries its table's name; the leverage table states its unit per
    # row, so the note says that instead of asserting a unit for it. The handoff's own words follow
    # in the handoff's order, nothing else added (rc2/delivered-notes.json, rulings n1 to n5).
    assert block.note == (
        f"Pro forma capitalisation: {' '.join(lines)} · Pro forma leverage: unit stated per row"
    )
    assert "REGISTER-MARKER-7" not in json.dumps(json.loads(files["report-view.json"])["blocks"])


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


# Golden digests computed from the 7f6a39dd tree (no `pro-forma` spec), never from this tree.
FULL_PRESET_GOLDEN = {
    "build": "97d3c7fa1d5b36009947edfe3a979ae9e8a2bec6887292cf7ba56c2088052799",
    "candidate-render": "1bab7fa718af30a5468f00bf24de7131bc3fc1540f565d678220267bf47db008",
    "accepted-render": "a1d09b347b2ed28b03aee44e7e409a79f1e30ff4ccb02584287456bef6d08bd5",
}


@pytest.mark.parametrize("mode", ["candidate", "accepted"])
def test_full_preset_build_and_render_are_byte_identical_to_the_old_tree(mode):
    """`build` and `render` never see run_type, so one view stands for Secondary and Primary."""
    view = View(run=RUN, mode=mode, modules=())
    pathway = next(p for p in pathways() if p.id == "credit_snapshot")
    report = build(view, pathway, SHIPPED_MAPS)
    assert len(report.blocks) == 12
    assert "pro-forma" not in [b.block_id for b in report.blocks]
    digest = hashlib.sha256(report.model_dump_json().encode()).hexdigest()
    assert digest == FULL_PRESET_GOLDEN["build"]
    html = hashlib.sha256(render(view).encode()).hexdigest()
    assert html == FULL_PRESET_GOLDEN[f"{mode}-render"]


def test_layout_only_block_stays_in_the_preset_and_passes_the_delivery_subset_check(tmp_path):
    preset = next(p for p in pathways() if p.id == "credit_snapshot")
    assert "pro-forma" in preset.blocks  # the layout may select it ...
    files = deliver(tmp_path, CP2_RUN, "CP-2", cp2_handoff("cp2-full-valid"), "primary")
    blocks = [b["block_id"] for b in json.loads(files["report-view.json"])["blocks"]]
    assert "pro-forma" in blocks  # ... and the markdown_delivery subset check accepts it


PARTNER = {
    "relative_value": (),
    "covenant_refinancing": ("CP-2D",),
    "distressed_restructuring": ("CP-2H",),
    "portfolio_decision": (),
}


@pytest.mark.parametrize("pathway", sorted(PARTNER))
def test_other_pathways_deliver_both_tables_intact_in_the_evidence_view(tmp_path, pathway):
    """Synthetic handoff (frozen key case), not a model run. These presets have no `pro-forma`
    block: both tables reach the report only as the generic evidence content of CP-2."""
    ordered = (*PARTNER[pathway], "CP-2")
    run = RUN.model_copy(update={"requested_modules": ordered, "pathway": pathway})
    layout, _ = _layout(run, ordered, (), "cfg", run_type="primary", legal_documents="executed")
    assert "pro-forma" not in layout.blocks
    findings = CASES["cp2-full-valid"]["findings"]
    specs = {}
    for module in ordered:
        body = ""
        for route in (r for r in layout.routes if r.module_id == module):
            body += f"### {route.heading}\n\n"
            body += (
                "Prose text.\n\n"
                if route.kind == "prose"
                else "| A | B |\n| --- | --- |\n| x | 1 |\n\n"
            )
        if module == "CP-2":
            body += findings + "\n\n"
        raw = (
            f"# {module} Acme Corp\n\n## Request\nAcme Corp.\n\n## Sources\nsrc.pdf\n\n"
            f"## Findings\n\n{body}{TAIL}"
        ).encode()
        (tmp_path / f"{module}.md").write_bytes(raw)
        specs[module] = HandoffInput(path=f"{module}.md", sha256=hashlib.sha256(raw).hexdigest())
    files = markdown_files(DeliveryRequest(run=run, handoffs=specs, layout=layout), tmp_path)
    shown = [b["block_id"] for b in json.loads(files["report-view.json"])["blocks"]]
    assert "pro-forma" not in shown
    module = next(m for m in json.loads(files["view.json"])["modules"] if m["module_id"] == "CP-2")
    facts = {f["fact_id"]: f["text"] for f in module["facts"]}
    html = files["report.html"].decode()
    for heading in ("Pro forma capitalisation", "Pro forma leverage"):
        table = next(t for t in module["tables"] if t["title"].startswith(f"{heading} — "))
        want = table_cells(findings, heading)
        got = [[row["label"], *(facts[fid] for fid in row["fact_ids"])] for row in table["rows"]]
        assert got == want
        for row in want:
            for cell in row:
                assert escape(cell) in html
    assert "Not supplied: not stated" in html
    for line in ("Balance-sheet date: 2014-06-30", "LTM period: LTM Q2 2014"):
        assert line in findings.splitlines()  # the key's own lines, so the assertion stays exact
        assert escape(line) in html
        assert line in files["view.json"].decode()
