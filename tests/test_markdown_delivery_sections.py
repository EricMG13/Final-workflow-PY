"""Synthetic regressions for what a routed section carries across the handoff boundary.

Scope: hand-written CP-1B handoffs through markdown_files; no retained model response and no
analytical run. Expected texts are written out from the handoff text below, not computed.
"""

import hashlib
import json
from pathlib import Path

import pytest

from deploy_vii.contracts import Run
from deploy_vii.report_view import ReportView
from deploy_workflow.handoff_delivery import DeliveryRequest
from deploy_workflow.markdown_delivery import (
    check_coverage,
    gap_limitations,
    literal_module,
    markdown_files,
    require_issuer,
)
from deploy_workflow.model_handoff_delivery import _literal_tables

TAIL = "## Calculations\nNone.\n## Gaps\nNone.\n## Next module\nDelivery.\n"


def handoff(request: str, findings: str, tail: str = TAIL) -> str:
    return (
        "# CP-1B TransDigm Group Incorporated\n## Request\n"
        + request
        + "\n## Sources\nNone.\n## Findings\n"
        + findings
        + "\n"
        + tail
    )


def deliver(
    tmp_path: Path,
    text: str,
    routes: list[dict],
    module: str = "CP-1B",
    execution: str | None = None,
) -> dict:
    raw = text.encode()
    path = tmp_path / (module + ".md")
    path.write_bytes(raw)
    request = DeliveryRequest.model_validate_json(
        json.dumps(
            {
                "run": {
                    "run_id": "r1",
                    "issuer_id": "TDG",
                    "issuer_name": "TransDigm Group Incorporated",
                    "as_of": "2024-12-28",
                    "case_kind": "public",
                    "pathway": "earnings_update",
                    "requested_modules": [module],
                },
                "handoffs": {
                    module: {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
                },
                "layout": {
                    "blocks": ["headline-results"],
                    "routes": [
                        {"module_id": module, "block_id": "headline-results", **r}
                        for r in routes
                        if r.get("block_id") != "front"
                    ],
                    "scope": "synthetic regression",
                    "front": [r for r in routes if r.get("block_id") == "front"],
                },
                **({} if execution is None else {"module_execution": {module: execution}}),
            }
        )
    )
    files = markdown_files(request, Path("/"))
    report = ReportView.model_validate_json(files["report-view.json"])
    return {"block": report.blocks[0], "files": files}


TABLE = "| Metric | FY2023 | FY2024 |\n|---|---:|---:|\n| Revenue | 1,000.5 | 1,200.0 |\n"
ROUTE = {"heading": "Financials", "kind": "table", "table_header": "Metric", "label": "Financials"}


def test_unit_and_limitation_sentences_of_the_routed_section_stay_with_the_table(tmp_path):
    # Hand-derived: the section's two paragraphs, one before and one after the table, are
    # joined in handoff order after the route label; the table is untouched.
    findings = (
        "### Financials\nAll amounts in EUR thousands.\n\n"
        + TABLE
        + "\nFY2024 is unaudited,\nsubject to restatement.\n"
    )
    got = deliver(tmp_path, handoff("Scope.", findings), [ROUTE])["block"]
    assert got.note == (
        "Financials · All amounts in EUR thousands. FY2024 is unaudited, subject to restatement."
    )
    assert got.columns == ("FY2023", "FY2024")
    assert [[c.text for c in r.cells] for r in got.rows] == [["1,000.5", "1,200.0"]]


def test_section_prose_is_not_removed_from_the_cited_evidence(tmp_path):
    findings = "### Financials\nAll amounts in EUR thousands.\n\n" + TABLE
    files = deliver(tmp_path, handoff("Scope.", findings), [ROUTE])["files"]
    view = json.loads(files["view.json"])
    facts = [f for m in view["modules"] for f in m["facts"] if f["table_id"].startswith("prose-")]
    cited = {f["text"]: [c["quote"] for c in f["citations"]] for f in facts}
    assert cited["All amounts in EUR thousands."] == ["All amounts in EUR thousands."]


def test_same_heading_in_two_sections_takes_only_its_own_prose(tmp_path):
    # Two "### Values" headings with different tables: each note holds its own section's line.
    findings = "### Values\nUnit one: USD millions.\n\n| Metric | A |\n|---|---|\n| X | 1 |\n"
    tail = (
        "## Calculations\n### Values\nUnit two: EUR thousands.\n\n"
        "| Item | B |\n|---|---|\n| Y | 2 |\n## Gaps\nNone.\n## Next module\nDelivery.\n"
    )
    text = handoff("Scope.", findings, tail)
    route = {"heading": "Values", "kind": "table", "table_header": "Metric"}
    assert deliver(tmp_path, text, [route])["block"].note == "Unit one: USD millions."
    route["table_header"] = "Item"
    assert deliver(tmp_path, text, [route])["block"].note == "Unit two: EUR thousands."


def test_table_section_without_prose_has_only_the_route_label(tmp_path):
    got = deliver(tmp_path, handoff("Scope.", "### Financials\n" + TABLE), [ROUTE])["block"]
    assert got.note == "Financials"
    unlabelled = {k: v for k, v in ROUTE.items() if k != "label"}
    got = deliver(tmp_path, handoff("Scope.", "### Financials\n" + TABLE), [unlabelled])["block"]
    assert got.note is None


PARAGRAPHS = "Earnings view: first.\n\nEarnings view: second.\n\nScope note, not selected.\n"
PROSE = {"heading": "Request", "kind": "prose", "prefix": "Earnings view"}


def test_partial_row_selection_is_one_register_not_one_tab_per_row(tmp_path):
    # Hand-derived: two of three paragraphs match, so they form the block's one register of two
    # rows in handoff order; the third paragraph is not shown here (it stays in Evidence).
    findings = "### Financials\n" + TABLE
    got = deliver(tmp_path, handoff(PARAGRAPHS, findings), [{**PROSE, "label": "View"}])["block"]
    assert got.tabs == () and got.tab_label is None
    assert [[c.text for c in r.cells] for r in got.rows] == [
        ["Earnings view: first."],
        ["Earnings view: second."],
    ]
    assert got.note == "View"


def test_two_partial_routes_with_different_labels_stay_two_tabs(tmp_path):
    text = handoff("Alpha one.\n\nBeta one.\n\nAlpha two.\n", "### Financials\n" + TABLE)
    routes = [
        {"heading": "Request", "kind": "prose", "prefix": "Alpha", "label": "A"},
        {"heading": "Request", "kind": "prose", "prefix": "Beta", "label": "B"},
    ]
    got = deliver(tmp_path, text, routes)["block"]
    assert got.tab_label == "A" and [t.label for t in got.tabs] == ["B"]
    assert [[c.text for c in r.cells] for r in got.rows] == [["Alpha one."], ["Alpha two."]]
    assert [[c.text for c in r.cells] for r in got.tabs[0].rows] == [["Beta one."]]


def test_full_selection_still_binds_the_whole_table(tmp_path):
    text = handoff("Earnings view: first.\n\nEarnings view: second.\n", "### Financials\n" + TABLE)
    got = deliver(tmp_path, text, [{**PROSE, "label": "View"}])["block"]
    assert got.tabs == ()
    assert [r.cells[0].text for r in got.rows] == [
        "Earnings view: first.",
        "Earnings view: second.",
    ]


def test_unselected_prefix_still_refuses(tmp_path):
    text = handoff("Other.\n", "### Financials\n" + TABLE)
    with pytest.raises(ValueError, match="markdown_selector"):
        deliver(tmp_path, text, [PROSE])


def test_two_routes_on_one_table_with_one_label_share_a_register_in_route_order(tmp_path):
    # Hand-derived: rows follow route order (Gamma route first), and no row is shown twice.
    text = handoff("Alpha one.\n\nGamma one.\n\nAlpha two.\n\nBeta.\n", "### Financials\n" + TABLE)
    routes = [
        {"heading": "Request", "kind": "prose", "prefix": "Gamma"},
        {"heading": "Request", "kind": "prose", "prefix": "Alpha"},
    ]
    got = deliver(tmp_path, text, routes)["block"]
    assert got.tabs == ()
    assert [r.cells[0].text for r in got.rows] == ["Gamma one.", "Alpha one.", "Alpha two."]


# Second-model review adversarial cases. Expected values are written out from the handoff text.


def test_two_tables_in_one_section_carry_its_sentences_once(tmp_path):
    # Both registers sit under one "### Financials": its two paragraphs appear once, in handoff
    # order, after the route labels; nothing is repeated per tab.
    findings = (
        "### Financials\nAmounts in USD millions.\n\n"
        + TABLE
        + "\nRatios are historical.\n\n| Item | FY2024 |\n|---|---:|\n| Cover | 2.5x |\n"
    )
    routes = [
        {"heading": "Financials", "kind": "table", "table_header": "Metric", "label": "P"},
        {"heading": "Financials", "kind": "table", "table_header": "Item", "label": "Q"},
    ]
    got = deliver(tmp_path, handoff("Scope.", findings), routes)["block"]
    assert got.tab_label == "P" and [t.label for t in got.tabs] == ["Q"]
    assert got.note == "P · Q · Amounts in USD millions. Ratios are historical."
    assert [[c.text for c in r.cells] for r in got.tabs[0].rows] == [["2.5x"]]


def test_tables_from_two_sections_keep_route_order_in_the_note(tmp_path):
    findings = (
        "### Financials\nAmounts in USD millions.\n\n"
        + TABLE
        + "\n### Cover\nCover uses cash interest.\n\n"
        + "| Item | FY2024 |\n|---|---:|\n| Cover | 2.5x |\n"
    )
    routes = [
        {"heading": "Cover", "kind": "table", "table_header": "Item", "label": "Q"},
        {"heading": "Financials", "kind": "table", "table_header": "Metric", "label": "P"},
    ]
    got = deliver(tmp_path, handoff("Scope.", findings), routes)["block"]
    assert got.tab_label == "Q" and [t.label for t in got.tabs] == ["P"]
    # Each section's sentences are one note element; elements are joined by " · ".
    assert got.note == "Q · P · Cover uses cash interest. · Amounts in USD millions."


def test_subsection_after_the_table_is_its_own_section(tmp_path):
    # "#### Other" starts a new section: its line is not in the note and stays cited in Evidence.
    findings = "### Financials\n**USD millions.**\n\n" + TABLE + "\n#### Other\nUnrelated line.\n"
    out = deliver(tmp_path, handoff("Scope.", findings), [ROUTE])
    assert out["block"].note == "Financials · USD millions."
    view = json.loads(out["files"]["view.json"])
    facts = [f for m in view["modules"] for f in m["facts"]]
    texts = [f["text"] for f in facts if f["table_id"].startswith("prose-")]
    assert "Unrelated line." in texts and "USD millions." in texts


def test_merged_register_rows_keep_their_own_citations(tmp_path):
    # Request lines: 3 Alpha one, 5 Beta one, 7 Gamma one, 9 Alpha two, 11 Omega.
    # Routes Alpha->X, Beta->Y, Gamma->X: X holds Alpha one, Alpha two, Gamma one (route order);
    # Y holds Beta one. Each cell cites its own paragraph line.
    request = "Alpha one.\n\nBeta one.\n\nGamma one.\n\nAlpha two.\n\nOmega.\n"
    routes = [
        {"heading": "Request", "kind": "prose", "prefix": "Alpha", "label": "X"},
        {"heading": "Request", "kind": "prose", "prefix": "Beta", "label": "Y"},
        {"heading": "Request", "kind": "prose", "prefix": "Gamma", "label": "X"},
    ]
    out = deliver(tmp_path, handoff(request, "### Financials\n" + TABLE), routes)
    got = out["block"]
    assert got.tab_label == "X" and [t.label for t in got.tabs] == ["Y"]
    assert got.note == "X · Y"
    report = json.loads(out["files"]["report-view.json"])
    fact_of = {ref: e["coord"]["fact_id"] for e in report["index"]["facts"] for ref in e["ref_ids"]}
    view = json.loads(out["files"]["view.json"])
    line_of = {
        f["fact_id"]: [c["locator"] for c in f["citations"]]
        for m in view["modules"]
        for f in m["facts"]
    }

    def shown(rows):
        return [(r.cells[0].text, line_of[fact_of[r.cells[0].ref_id]]) for r in rows]

    assert shown(got.rows) == [
        ("Alpha one.", ["line 3"]),
        ("Alpha two.", ["line 9"]),
        ("Gamma one.", ["line 7"]),
    ]
    assert shown(got.tabs[0].rows) == [("Beta one.", ["line 5"])]


def test_one_label_on_two_different_tables_still_refuses(tmp_path):
    # The merge is per table: the same label on registers of two tables is a real clash.
    findings = "### Financials\nAlpha f.\n\nOther f.\n\n" + TABLE
    routes = [
        {"heading": "Request", "kind": "prose", "prefix": "Alpha", "label": "X"},
        {"heading": "Financials", "kind": "prose", "prefix": "Alpha", "label": "X"},
    ]
    with pytest.raises(ValueError, match="Tab labels are distinct"):
        deliver(tmp_path, handoff("Alpha r.\n\nBeta r.\n", findings), routes)


ISSUER_RUN = Run.model_validate_json(
    json.dumps(
        {
            "run_id": "r1",
            "issuer_id": "FRD",
            "issuer_name": "Ford",
            "as_of": "2024-12-28",
            "case_kind": "public",
            "pathway": "earnings_update",
            "requested_modules": ["CP-1B"],
        }
    )
)


@pytest.mark.parametrize(
    ("issuer", "aliases", "title", "body"),
    [
        # "Ford" is the last four letters of "Stanford" and "AB" the middle of "lab": a name
        # touching a letter on either side is another word, not this issuer.
        ("Ford", (), "# CP-1B Stanford Health Care", "Analyse Stanford bonds."),
        ("Ford", (), "# CP-1B Fordham Capital", "Analyse Fordham bonds."),
        ("Absolute Lab Inc", ("AB",), "# CP-1B Acme Corp", "Analyse Acme lab capacity."),
    ],
)
def test_issuer_name_or_alias_inside_another_word_is_refused(issuer, aliases, title, body):
    run = ISSUER_RUN.model_copy(update={"issuer_name": issuer})
    lines = [title, "## Request", body]
    with pytest.raises(ValueError, match="markdown_issuer"):
        require_issuer(run, aliases, "CP-1B", lines)


@pytest.mark.parametrize(
    ("aliases", "title", "body"),
    [
        ((), "# CP-1B Ford Motor", "x"),
        ((), "# CP-1B Analysis", "Credit view of FORD,\nthe automaker."),
        (("AB",), "# CP-1B Analysis", "AB (the issuer) reported."),
        (("Ford Otomotiv Sanayi",), "# CP-1B Analysis", "Analyse Ford Otomotiv\nSanayi A.S."),
    ],
)
def test_issuer_name_or_alias_as_whole_words_is_accepted(aliases, title, body):
    lines = [title, "## Request", *body.splitlines()]
    run = ISSUER_RUN if aliases == () else ISSUER_RUN.model_copy(update={"issuer_name": "Other"})
    require_issuer(run, aliases, "CP-1B", lines)


def prose_of(text: str, heading: str) -> list[tuple[str, list[str]]]:
    """(text, cited line numbers) of every prose fact under `heading`, in handoff order."""
    module, _, meta = literal_module("CP-1B", text.encode())
    return [
        (f.text, [int(c.locator.split()[-1]) for c in f.citations])
        for f in module.facts
        if meta.get(f.table_id) == (heading, "prose")
    ]


def test_list_items_are_one_fact_each_and_a_prefix_route_reaches_an_item(tmp_path):
    # Hand-derived: line 7 is "### Watch", so its four items sit on lines 8 to 11, one fact each.
    # plain() drops the backticks of line 9 only; the "- " and "1. " markers stay in the text.
    findings = (
        "### Watch\n- Track cash interest\n- Track `covenant` headroom\n1. First\n2. Second\n"
    )
    text = handoff("Scope.", findings)
    assert prose_of(text, "Watch") == [
        ("- Track cash interest", [8]),
        ("- Track covenant headroom", [9]),
        ("1. First", [10]),
        ("2. Second", [11]),
    ]
    route = {"heading": "Watch", "kind": "prose", "prefix": "Track covenant"}
    got = deliver(tmp_path, text, [route])["block"]
    assert [[c.text for c in r.cells] for r in got.rows] == [["- Track covenant headroom"]]
    route["prefix"] = "2. Sec"
    got = deliver(tmp_path, text, [route])["block"]
    assert [[c.text for c in r.cells] for r in got.rows] == [["2. Second"]]


def test_fenced_block_is_one_fact_kept_as_written(tmp_path):
    # Hand-derived: lines 8 "Before.", 9-11 the fence with its JSON line, 12 "After.". The fenced
    # text keeps its backticks; the fences are part of the quoted lines.
    findings = '### Cfg\nBefore.\n```json\n{"a": 1}\n```\nAfter.\n'
    assert prose_of(handoff("Scope.", findings), "Cfg") == [
        ("Before.", [8]),
        ('```json {"a": 1} ```', [9, 10, 11]),
        ("After.", [12]),
    ]


def test_pipe_lines_outside_a_table_are_kept_as_prose_not_dropped():
    # Hand-derived: lines 8-10 have no |---| separator, so they form no table. Each stays a fact
    # of its own with its line; the real table (lines 11-13) is a table, not prose.
    findings = (
        "### Covenants\n| Covenant | Headroom |\n| Net leverage 7.25x | ROW-ONE |\n"
        "|Pipe-led caveat\n| Real | Value |\n|---|---|\n| A | 1 |\n"
    )
    text = handoff("Scope.", findings)
    assert prose_of(text, "Covenants") == [
        ("| Covenant | Headroom |", [8]),
        ("| Net leverage 7.25x | ROW-ONE |", [9]),
        ("|Pipe-led caveat", [10]),
    ]
    module, _, meta = literal_module("CP-1B", text.encode())
    tables = [t for t in module.tables if meta[t.table_id] == ("Covenants", "table")]
    assert [(t.row_header, [r.label for r in t.rows]) for t in tables] == [("Real", ["A"])]


def test_hash_without_a_space_is_text_not_a_heading():
    # Hand-derived: "#1 risk ..." (line 8) and "#NoSpace" (line 10) are paragraph text under
    # "### Risks"; seven hashes is not a heading either. Lines 8-9 wrap into one paragraph.
    findings = "### Risks\n#1 risk is the 2027 wall.\nSecond sentence.\n\n#NoSpace\n####### seven\n"
    assert prose_of(handoff("Scope.", findings), "Risks") == [
        ("#1 risk is the 2027 wall. Second sentence.", [8, 9]),
        ("#NoSpace ####### seven", [11, 12]),
    ]


NOTES = (
    "# CP-1B TransDigm Group Incorporated\n## Request\nScope.\n## Sources\nNone.\n"
    "## Findings\n### Notes\nFindings note one.\n## Calculations\n### Notes\n"
    "Calculation note two.\n## Gaps\nNone.\n## Next module\nDelivery.\n"
)


def test_same_named_subsections_stay_apart_and_routes_address_the_path(tmp_path):
    # Hand-derived: "### Notes" is on line 7 (under Findings) and line 10 (under Calculations).
    module, _, meta = literal_module("CP-1B", NOTES.encode())
    found = {
        meta[t.table_id][0]: [f.text for f in module.facts if f.table_id == t.table_id]
        for t in module.tables
        if t.table_id.startswith("prose-")
    }
    assert found["Findings > Notes"] == ["Findings note one."]
    assert found["Calculations > Notes"] == ["Calculation note two."]
    assert "Notes" not in found
    with pytest.raises(ValueError, match="markdown_selector"):
        deliver(tmp_path, NOTES, [{"heading": "Notes", "kind": "prose"}])
    route = {"heading": "Findings > Notes", "kind": "prose", "label": "Findings notes"}
    got = deliver(tmp_path, NOTES, [route])["block"]
    assert [[c.text for c in r.cells] for r in got.rows] == [["Findings note one."]]
    assert got.note == "Findings notes"


def test_a_repeated_heading_path_is_told_apart_by_its_line(tmp_path):
    # Hand-derived: two "### Notes" under one "## Findings" (lines 7 and 9) share a path, so the
    # label adds the first line of each group (8 and 10).
    text = NOTES.replace("## Calculations\n### Notes\nCalculation", "### Notes\nCalculation")
    text = text.replace("## Gaps", "## Calculations\nNone.\n## Gaps")
    module, _, meta = literal_module("CP-1B", text.encode())
    labels = [meta[t.table_id][0] for t in module.tables if "Notes" in meta[t.table_id][0]]
    assert labels == ["Findings > Notes (line 8)", "Findings > Notes (line 10)"]


def test_raw_table_titles_follow_the_nearest_heading_not_earlier_bold_prose():
    # Hand-derived: each table is titled by the heading line before it (## resets the title);
    # a bold lead-in that is only part of a line never becomes a title, a whole-line bold does.
    raw = (
        "# CP-2 TDG\n## Request\nTDG.\n## Sources\nNone.\n## Findings\n"
        "**Assessment —** Leverage is high.\n| M | FY |\n|---|---|\n| R | 1 |\n"
        "**Metrics**\n| N | FY |\n|---|---|\n| S | 2 |\n"
        "## Calculations\n| C | V |\n|---|---|\n| X | 3 |\n"
        "### Detail\n| D | V |\n|---|---|\n| Y | 4 |\n"
        "## Gaps\nNone.\n## Next module\nDelivery.\n"
    ).encode()
    _, _, tables, _ = _literal_tables("current_synthesis", raw, hashlib.sha256(raw).hexdigest())
    assert [t.title for t in tables] == [
        "current_synthesis: Findings",
        "current_synthesis: Metrics",
        "current_synthesis: Calculations",
        "current_synthesis: Detail",
    ]


FENCE_TABLE = "| M | FY |\n|---|---|\n| R | 1 |\n"


def _tables_in(findings: str) -> list[str]:
    raw = (
        "# CP-2 TDG\n## Request\nTDG.\n## Sources\nNone.\n## Findings\n" + findings
    ).encode() + b"## Calculations\nNone.\n## Gaps\nNone.\n## Next module\nDelivery.\n"
    _, _, tables, _ = _literal_tables("current_synthesis", raw, hashlib.sha256(raw).hexdigest())
    return [t.title for t in tables]


@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_a_pipe_table_inside_a_fence_is_not_a_table_but_the_same_table_outside_is(fence):
    assert _tables_in(f"{fence}\n{FENCE_TABLE}{fence}\n") == []
    assert _tables_in(f"{fence}\n{fence}\n{FENCE_TABLE}") == ["current_synthesis: Findings"]


def test_a_fence_left_open_ends_at_its_section_for_the_table_reader():
    # The fence opened under Findings is never closed; "## Calculations" ends it, so the table
    # written under Calculations is still a table and the one inside the fence is not.
    raw = (
        "# CP-2 TDG\n## Request\nTDG.\n## Sources\nNone.\n## Findings\n```\n"
        + FENCE_TABLE
        + "## Calculations\n| C | V |\n|---|---|\n| X | 3 |\n## Gaps\nNone.\n## Next module\nD.\n"
    ).encode()
    _, _, tables, _ = _literal_tables("current_synthesis", raw, hashlib.sha256(raw).hexdigest())
    assert [t.title for t in tables] == ["current_synthesis: Calculations"]


def test_wrapped_list_item_stays_whole_and_an_unclosed_fence_ends_at_its_section():
    # Hand-derived: line 8 starts an item that wraps onto line 9; line 10 is the next item.
    # The fence opened on line 13 is never closed (its blank line 15 is not quoted); the
    # "## Calculations" heading ends it, so Calculations still holds its own "None.".
    findings = "### Watch\n- Track cash\n  interest.\n- Second.\n\n### Code\n```\nx = 1\n\ny = 2\n"
    text = handoff("Scope.", findings)
    assert prose_of(text, "Watch") == [("- Track cash interest.", [8, 9]), ("- Second.", [10])]
    assert prose_of(text, "Code") == [("``` x = 1 y = 2", [13, 14, 16])]
    assert [t for t, _ in prose_of(text, "Calculations")] == ["None."]


@pytest.mark.parametrize(
    "text",
    ["Ford's notes are secured.", "Ford’s notes are secured.", "Ford-owned notes.", "FORD, Inc."],
)
def test_issuer_name_beside_a_possessive_hyphen_or_comma_is_accepted(text):
    require_issuer(ISSUER_RUN, (), "CP-1B", ["# CP-1B Analysis", "## Request", text])


def test_a_wrapped_item_line_opening_with_a_year_or_parenthesised_number_is_not_a_new_item():
    # Hand-derived: "2024." has four digits, so line 9 continues the item on line 8; "1)" and
    # "2)" (lines 10 and 11) are items of their own; "  - nested" (line 12) is a new item.
    findings = (
        "### Watch\n- Leverage fell in\n2024. Revenue rose.\n1) First\n2) Second\n  - nested\n"
    )
    assert prose_of(handoff("Scope.", findings), "Watch") == [
        ("- Leverage fell in 2024. Revenue rose.", [8, 9]),
        ("1) First", [10]),
        ("2) Second", [11]),
        ("- nested", [12]),
    ]


FIXED = (
    "Literal checked analytical handoff, not native contract acceptance; "
    "source qualifications and gaps remain."
)


def gaps_of(gaps: str) -> tuple[str, ...]:
    tail = "## Calculations\nNone.\n## Gaps\n" + gaps + "## Next module\nDelivery.\n"
    view = literal_module("CP-1B", handoff("Scope.", "### F\n" + TABLE, tail).encode())[0]
    assert view.limitations[0] == FIXED
    return view.limitations[1:]


def test_each_gap_row_and_paragraph_becomes_a_module_limitation():
    gaps = (
        "| ID | Item | Status |\n|---|---|---|\n"
        "| G1 | Revolver availability | Not supplied |\n"
        "| G2 | Lease detail | Not supplied |\n\n"
        "Market inputs were not supplied.\n"
    )
    assert gaps_of(gaps) == (
        "G1; Revolver availability; Not supplied",
        "G2; Lease detail; Not supplied",
        "Market inputs were not supplied.",
    )


def test_prose_gaps_comments_and_subheadings():
    gaps = (
        "<!-- hidden gap\n| X | Y |\n|---|---|\n| H | hidden |\n-->\n"
        "### Assurance limits\nThe audit opinion was\nnot supplied.\n\n"
        "### Data\n| A | B |\n|---|---|\n| **Cash** | `n/a` |\n\n"
        "Second paragraph.\n"
    )
    assert gaps_of(gaps) == (
        "The audit opinion was not supplied.",
        "Cash; n/a",
        "Second paragraph.",
    )


def test_a_gaps_subsection_elsewhere_does_not_refuse_the_gaps_section():
    raw = (
        "# CP-1B X\n## Findings\n### Gaps\nA subsection note.\n"
        "## Gaps\n| ID | Item |\n|---|---|\n| G1 | Lease detail |\n\nMarket data missing.\n"
        "## Next module\nDelivery.\n"
    )
    assert gap_limitations(raw) == ("G1; Lease detail", "Market data missing.")
    assert gap_limitations("# X\n## Findings\n### Gaps\nOnly here.\n") == ("Only here.",)


def test_a_handoff_without_gaps_keeps_only_the_fixed_limitation():
    # literal_module needs the six headings, so a handoff with no Gaps section is read directly.
    raw = "# CP-1B X\n## Request\nScope.\n## Findings\nText.\n"
    assert gap_limitations(raw) == ()
    assert gaps_of("None.\n") == ()


def test_a_fenced_block_in_gaps_yields_no_limitation():
    gaps = "Before.\n```\nNot a gap.\n| X | Y |\n|---|---|\n| H | hidden |\n```\nAfter.\n"
    assert gaps_of(gaps) == ("Before.", "After.")


def test_a_table_row_with_empty_cells_yields_no_limitation():
    # The handoff reader refuses such a row elsewhere; gap_limitations is called on its own too.
    raw = "## Gaps\n| ID | Item |\n|---|---|\n| | |\n|  |\n| G1 | Lease detail |\n"
    assert gap_limitations(raw) == ("G1; Lease detail",)


COVERED = (
    "# CP-1B TransDigm Group Incorporated\n"  # 1
    "## Request\nScope.\n"  # 2-3
    "## Sources\nNone.\n"  # 4-5
    "## Findings\n"  # 6: no content of its own
    "### Financials\nAmounts in USD millions.\n\n"  # 7-9
    "| Metric | FY2023 | FY2024 |\n|---|---:|---:|\n| Revenue | 1,000.5 | 1,200.0 |\n\n"  # 10-13
    "### Notes\nMargin held.\n"  # 14-15
    "## Calculations\nNone.\n## Gaps\nNone.\n## Next module\nDelivery.\n"  # 16-21
)


def coverage_of(files: dict) -> dict:
    return json.loads(files["coverage.json"])


def test_every_heading_with_content_is_in_the_coverage_record(tmp_path):
    files = deliver(tmp_path, COVERED, [ROUTE])["files"]
    entries = coverage_of(files)["modules"]["CP-1B"]
    assert sorted(e["line"] for e in entries) == [2, 4, 7, 7, 14, 16, 18, 20]
    assert coverage_of(files)["schema"] == "delivery-coverage/1"
    assert "coverage.json" in json.loads(files["delivery.json"])["files"]


def test_routed_sections_name_their_block_and_the_rest_name_evidence(tmp_path):
    entries = coverage_of(deliver(tmp_path, COVERED, [ROUTE])["files"])["modules"]["CP-1B"]
    seen = {(e["line"], e["kind"]): (e["heading"], e["blocks"]) for e in entries}
    assert seen[(7, "table")] == ("Financials", ["headline-results"])
    assert seen[(7, "prose")] == ("Financials", ["evidence"])
    assert seen[(14, "prose")] == ("Notes", ["evidence"])
    assert seen[(2, "prose")] == ("Request", ["evidence"])


def drop_prose_group(monkeypatch, heading: str) -> None:
    from deploy_workflow import markdown_delivery as md

    real = md._prose_groups
    monkeypatch.setattr(
        md, "_prose_groups", lambda lines, t: [g for g in real(lines, t) if g.heading != heading]
    )


def test_a_dropped_section_fails_the_build(tmp_path, monkeypatch):
    drop_prose_group(monkeypatch, "Notes")
    with pytest.raises(
        ValueError, match=r"delivery_coverage: CP-1B line 14 Notes is not presented"
    ):
        deliver(tmp_path, COVERED, [ROUTE])


def test_check_coverage_ignores_fenced_commented_and_empty_headings():
    raw = (
        "# T\n## A\n<!-- c -->\n### B\n"  # 1-4: A and B have no content
        "## C\n```\n### inside\n```\n"  # 5-8: C has content; the fenced heading is code
        "## D\n| x |\n"  # 9-10
    )
    with pytest.raises(ValueError, match="M line 9 D is not presented"):
        check_coverage({"M": raw}, {"modules": {"M": [{"line": 5, "kind": "prose"}]}})
    check_coverage(
        {"M": raw}, {"modules": {"M": [{"line": 5, "kind": "prose"}, {"line": 9, "kind": "prose"}]}}
    )


RECOVERY = Path(__file__).parent.parent / (
    "runs/cpos-sol-remaining-20261105/recovery/execution/"
    "delivery-94f5c089fa806476746a0df4d861ed406930b92f8208246f18d0cc08c2ebddca.json"
)


@pytest.mark.skipif(not RECOVERY.exists(), reason="retained recovery run is not checked out")
def test_recovery_handoffs_are_fully_covered():
    request = DeliveryRequest.model_validate_json(RECOVERY.read_text())
    files = markdown_files(request, RECOVERY.parent)  # builds in memory; nothing is written
    modules = coverage_of(files)["modules"]
    assert set(modules) == set(request.handoffs)
    assert all(modules[m] for m in modules)


def test_a_section_routed_in_part_names_every_block_its_rows_reach(tmp_path):
    two = COVERED.replace(
        "### Notes\nMargin held.\n", "### Notes\nMargin held.\n\nLeverage fell.\n"
    )
    route = {"heading": "Notes", "kind": "prose", "prefix": "Margin"}
    entries = coverage_of(deliver(tmp_path, two, [route])["files"])["modules"]["CP-1B"]
    notes = next(e for e in entries if e["heading"] == "Notes")
    assert notes["blocks"] == ["headline-results", "evidence"]


def test_a_dropped_prose_group_is_refused_though_a_table_shares_its_heading(tmp_path, monkeypatch):
    drop_prose_group(monkeypatch, "Financials")
    with pytest.raises(ValueError, match=r"CP-1B line 7 Financials is not presented"):
        deliver(tmp_path, COVERED, [ROUTE])


def test_a_table_entry_does_not_present_a_heading_with_only_a_table_dropped():
    raw = "## A\nText.\n| x | y |\n|---|---|\n| 1 | 2 |\n"
    with pytest.raises(ValueError, match="M line 1 A is not presented"):
        check_coverage({"M": raw}, {"modules": {"M": [{"line": 1, "kind": "prose"}]}})
    check_coverage(
        {"M": raw}, {"modules": {"M": [{"line": 1, "kind": "prose"}, {"line": 1, "kind": "table"}]}}
    )


def test_content_under_a_level_four_heading_is_checked():
    raw = "## A\n#### Deep\nText.\n"
    with pytest.raises(ValueError, match="M line 2 Deep is not presented"):
        check_coverage({"M": raw}, {"modules": {"M": []}})


@pytest.mark.parametrize(
    "findings",
    [
        "### F\n| Metric | FY2023 |\n|---|---\n| Revenue | 1 |\n",
        "### F\n| Metric | FY2023 |\n|\t---\t|\t---\t|\n| Revenue | 1 |\n",
        "### F\n| Metric | FY2023 |\n|---|---| \n| Revenue | 1 |\n",
    ],
)
def test_pipe_lines_the_reader_does_not_take_as_a_table_are_prose_not_a_missing_table(
    tmp_path, findings
):
    # Expected from the reader's rule (separator `|[ :|-]+|`, unstripped): no table in any case.
    deliver(tmp_path, handoff("Scope.", findings), [{"heading": "Request", "kind": "prose"}])


def test_a_stray_pipe_line_before_a_real_table_still_finds_the_table():
    raw = "## A\n| stray\n| x | y |\n|---|---|\n| 1 | 2 |\n"
    with pytest.raises(ValueError, match=r"M line 1 A is not presented \(table\)"):
        check_coverage({"M": raw}, {"modules": {"M": [{"line": 1, "kind": "prose"}]}})


# Handoff lines: Reader summary heading 7, its first data row 10, Action Bias heading 16, 17.
CP6_FINDINGS = (
    "### Reader summary\n| Bottom line | Confidence | Main limitation |\n|---|---|---|\n"
    "| Hold the position. | Moderate | Quarter data unaudited. |\n\n"
    "| Finding | Creditor impact | Confidence |\n|---|---|---|\n| Leverage | Higher | Low |\n\n"
    "### Action Bias Determination\n"
    "Final Action Bias: Watchlist. Spreads do not pay for the risk.\n\n"
    "### Financials\n" + TABLE
)
ACTION_BIAS = {"kind": "prose", "prefix": "Final Action Bias:"}
TABLE_FRONT = {"kind": "table", "table_header": "Bottom line | Confidence | Main limitation"}
FRONT = [
    {"module_id": "CP-6", "block_id": "front", "label": label, "heading": heading, **rest}
    for label, heading, rest in (
        ("Committee decision", "Reader summary", TABLE_FRONT),
        ("Committee action bias", "Action Bias Determination", ACTION_BIAS),
    )
]


def deliver_cp6(tmp_path: Path, text: str, front: list[dict], execution: str | None = None):
    return deliver(tmp_path, text, [ROUTE, *front], "CP-6", execution)["files"]


def cp6_text(findings: str = CP6_FINDINGS) -> str:
    return handoff("Scope.", findings).replace("# CP-1B", "# CP-6")


def test_front_routes_put_the_cited_line_above_the_call(tmp_path):
    files = deliver_cp6(tmp_path, cp6_text(), FRONT)
    html_text = files["report.html"].decode()
    assert '<section id="delivery-limits" class="banner" role="note">' in html_text
    assert (
        "Committee decision: confidence Moderate; main limitation: Quarter data unaudited. "
        "(CP-6 line 10)"
    ) in html_text
    assert (
        "<li>Final Action Bias: Watchlist. Spreads do not pay for the risk. (CP-6 line 17)</li>"
    ) in html_text
    assert html_text.index('id="delivery-limits"') < html_text.index('id="call-root"')
    coverage = json.loads(files["coverage.json"])["modules"]["CP-6"]
    fronted = {(e["kind"], e["line"]) for e in coverage if "front" in e["blocks"]}
    assert fronted == {("table", 7), ("prose", 16)}


def test_a_front_route_with_no_match_says_not_stated(tmp_path):
    text = cp6_text(CP6_FINDINGS.replace("Final Action Bias:", "Bias:"))
    html_text = deliver_cp6(tmp_path, text, FRONT)["report.html"].decode()
    assert "Committee action bias: not stated in the handoff" in html_text
    assert "<li>Committee decision: confidence Moderate;" in html_text


def test_front_text_is_escaped(tmp_path):
    text = cp6_text(CP6_FINDINGS.replace("Quarter data unaudited.", "A <b>&</b> B."))
    html_text = deliver_cp6(tmp_path, text, FRONT)["report.html"].decode()
    assert "main limitation: A &lt;b&gt;&amp;&lt;/b&gt; B. (CP-6 line 10)" in html_text


LIVE_WORDS = (
    "Produced by a live model run and accepted by the CP-OS check; not native contract acceptance."
)


@pytest.mark.parametrize(
    ("execution", "sentence"),
    [
        ("live-provider", LIVE_WORDS),
        (
            "retained-response-replay",
            "Replayed from a retained response; no new model call was made.",
        ),
        ("host-session", "Produced in a host session and accepted by the CP-OS check."),
        ("synthetic", "Synthetic test content, not issuer analysis."),
        (None, FIXED),  # no execution given: the fixed limitation stays first, no front section
    ],
)
def test_live_execution_reaches_each_module_limitation(tmp_path, execution, sentence):
    files = deliver_cp6(tmp_path, cp6_text(), [], execution)
    module = json.loads(files["view.json"])["modules"][0]
    assert module["limitations"][0] == sentence
    assert module["status"] == "candidate"
    assert "delivery-limits" not in files["report.html"].decode()


RETAINED_LAYOUT_MANIFESTS = [
    "runs/cpos-sol-medium-20261105/delivery-a2b23229572f1704c8b932bf2fbe41b76b5e3614fed7577d56b6f44f2cbc4053.json",
    "runs/cpos-launch-cp2-reader-001/delivery-593bc6819bec6be2624a19fef19f4702fe424c88c2a5fb916b0ac8375f461fca.json",
    "runs/cpos-launch-live-002/delivery-1b851b108d950efee6a7638c8754ebcd8531aa2635fcef1b892bdb0e52d80814.json",
    "runs/cpos-sol-remaining-20261105/recovery/execution/delivery-94f5c089fa806476746a0df4d861ed406930b92f8208246f18d0cc08c2ebddca.json",
    "runs/cpos-tdg-fresh-001/execution/delivery-5e88643b42cb134a0ac0d826f0841215f817d7db79a4a2d3abdab150efb6b272.json",
    "runs/cpos-tdg-fresh-001/execution/delivery-98ceb8fec71b78d4288cc7ad8c8ffff72c1a50bce4aa42999ca72682edbe09f1.json",
    "runs/web-04cd5a5d02ea7d1dea714a8a6632cd21/delivery-81e5fda8cf24771b8979b3da4cd6d51b60e4804133383e0b3b8f102b93821cae.json",
]


@pytest.mark.parametrize("name", RETAINED_LAYOUT_MANIFESTS)
def test_existing_layout_manifests_serialise_unchanged(name):
    # The seven of 24 retained layout manifests that round-tripped at a06406a2; the rest were
    # written by older schemas. New optional fields must not alter these bytes.
    raw = (Path(__file__).resolve().parent.parent / name).read_bytes()
    assert DeliveryRequest.model_validate_json(raw).model_dump_json(indent=2).encode() == raw
