"""Task 10: CP-4 reviews draft and marketing documents as Provisional, and the label reaches its
consumers. The cases are the frozen answer key
tests/fixtures/primary-provisional/checker-cases.json;
the expected issue categories are read from it, never computed here."""

import hashlib
import json
import re
from pathlib import Path

import pytest
from test_cpos_launch import AS_OF, answer, context_file, issuer_folder

from deploy_vii.cp4_legal import DRAFT_LIMITATION
from deploy_workflow.model.handoff import TOOLS
from deploy_workflow.model.providers import build
from deploy_workflow.model.turn import Message, ModelSpec, TurnRequest
from deploy_workflow.model_testing.configs import CONFIGS
from deploy_workflow.owners import cpos_launch
from deploy_workflow.owners.cpos import HandoffTask, _checked_handoff
from deploy_workflow.owners.cpos_launch import checker, prepare

ROOT = Path(__file__).resolve().parents[1]
KEY = json.loads((ROOT / "tests/fixtures/primary-provisional/checker-cases.json").read_text())
CASES = KEY["cases"]
# The key writes the fixed texts as placeholders; the real constants replace them here.
PLACEHOLDERS = {
    "{DRAFT_LIMITATION}": DRAFT_LIMITATION,
    "{FINAL_OM_REASON}": "After closing, the final offering memorandum is a summary of the "
    "executed documents, not the governing document.",
    "{BLOCKED_LINE}": "Module Status: Blocked",
}
CONSUMERS = ("CP-3", "CP-5", "CP-6")


DEAL_TERM = {
    "facility_id": "TLB",
    "instrument": "term loan",
    "currency": "USD",
    "size_m": "500",
    "tenor_years": "7",
    "talk_spread_bps_low": "350",
    "talk_spread_bps_high": "375",
    "talk_oid_low": "99",
    "talk_oid_high": "99.5",
    "floor_pct": "0.5",
    "call_protection": "101 soft call, 6 months",
    "use_of_proceeds": "Refinancing",
    "as_of": AS_OF,
    "provider": "Synthetic",
}


def fill(text: str | None) -> str:
    for placeholder, real in PLACEHOLDERS.items():
        text = (text or "").replace(placeholder, real)
    return text


def prepared_for(tmp_path: Path, pathway: str, run_type: str, legal: str, modules=None):
    path = context_file(tmp_path, pathway)
    data = json.loads(path.read_text())
    data["run"]["run_type"] = run_type
    data["attachments"]["legal_documents"] = legal
    data["identity"]["issue_classification"] = "high_yield"
    if run_type == "primary":  # The context refuses a Primary run without a facility row.
        data["deal_terms"] = [DEAL_TERM]
    path.write_text(json.dumps(data))
    return prepare(
        path,
        issuer_folder(tmp_path),
        tmp_path / "out",
        config="sol-medium",
        cap="50",
        modules=tuple(modules) if modules else None,
    )


def instructions_of(prepared, module: str) -> bytes:
    return (prepared.directory / "instructions" / f"{module}.md").read_bytes()


def case_answer(case: dict, prepared) -> str:
    module = case["module"]
    context = {
        "module_id": module,
        "sources": {"annual.txt": hashlib.sha256(b"Net sales").hexdigest()},
        "handoffs": {},
    }
    for name, raw in case_handoffs(case).items():
        context["handoffs"][name] = {"sha256": hashlib.sha256(raw).hexdigest()}
    routes = list(prepared.plan.layout.routes)
    text = answer(context, routes)
    given = case["answer"]
    if given["main_limitation"] is not None:
        old = "| Low | Synthetic data only. |"
        assert old in text
        text = text.replace(old, f"| Low | {fill(given['main_limitation'])} |")
    if given["routed_sections_text"] is not None:
        for route in routes:
            if route.module_id == module:
                head = f"### {route.heading}\n\n"
                assert head in text
                text = text.replace(head, head + fill(given["routed_sections_text"]) + "\n\n")
    view = "The issuer's credit view, stated first.\n\n"
    assert view in text
    text = text.replace(view, view + (fill(given["findings_text"]) + "\n\n").lstrip())
    if given["register"] is not None:
        heading = "### Legal document register\n\n" + given["register"] + "\n\n"
        text = text.replace("## Calculations", heading + "## Calculations", 1)
    return text


def case_handoffs(case: dict) -> dict[str, bytes]:
    if case["module"] == "CP-4":
        return {"CP-1": b"# upstream"}
    handoffs = {"CP-1": b"# upstream"}
    if case["upstream_cp4"] is not None:
        handoffs["CP-4"] = fill(case["upstream_cp4"]).encode()
    return handoffs


def new_categories(issues: tuple[str, ...]) -> set[str]:
    found = set()
    for issue in issues:
        for category, prefix in cpos_launch.PROVISIONAL_ISSUES.items():
            if issue.startswith(prefix):
                found.add(category)
    return found


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_checker_matches_the_frozen_answer_key(tmp_path, case):
    modules = [m for m in case.get("modules", ()) if m != "CP-MODEL"]
    prepared = prepared_for(
        tmp_path, case["pathway"], case["run_type"], case["legal_documents"], modules
    )
    raw = case_answer(case, prepared)
    task = HandoffTask(
        prepared.plan.run,
        case["module"],
        instructions_of(prepared, case["module"]),
        {"annual.txt": b"Net sales", "context": b"{}"},
        case_handoffs(case),
        1,
        (),
    )
    issues = _checked_handoff(task, raw.encode(), checker(prepared.layout))
    assert new_categories(issues) == set(case["expected"]["issues"]), issues
    # Nothing else is wrong with the synthetic answer, so acceptance is the key's verdict.
    assert (issues == ()) == case["expected"]["accepted"], issues


def test_constants_hold_the_contract_texts():
    assert cpos_launch.PROVISIONAL_PARAGRAPH
    assert cpos_launch.FINAL_OM_REASON == PLACEHOLDERS["{FINAL_OM_REASON}"]
    assert cpos_launch.BLOCKED_LINE == PLACEHOLDERS["{BLOCKED_LINE}"]
    assert cpos_launch.CONSUMER_SENTENCE == (
        "Label any term taken from a Provisional CP-4 handoff as Provisional."
    )
    for text in (DRAFT_LIMITATION, cpos_launch.FINAL_OM_REASON, cpos_launch.BLOCKED_LINE):
        assert text in cpos_launch.PROVISIONAL_PARAGRAPH


SCOPES = [
    ("primary", "draft", True),
    ("primary", "executed", True),
    ("primary", "none", True),
    ("secondary", "draft", True),
    ("secondary", "executed", False),
    ("secondary", "none", False),
]


@pytest.mark.parametrize(("run_type", "legal", "in_scope"), SCOPES)
def test_the_paragraph_and_consumer_sentence_appear_only_in_provisional_scope(
    tmp_path, run_type, legal, in_scope
):
    prepared = prepared_for(tmp_path, "credit_snapshot", run_type, legal)
    paragraph = cpos_launch.PROVISIONAL_PARAGRAPH.encode()
    sentence = cpos_launch.CONSUMER_SENTENCE.encode()
    assert {"CP-4", *CONSUMERS} <= set(prepared.ordered)
    for module in prepared.ordered:
        raw = instructions_of(prepared, module)
        assert raw.count(paragraph) == (1 if in_scope and module == "CP-4" else 0), module
        assert raw.count(sentence) == (1 if in_scope and module in CONSUMERS else 0), module
    if in_scope:
        raw = instructions_of(prepared, "CP-4")
        assert raw.index(paragraph) < raw.index(b"Selected method, verbatim:")
        assert raw.index(b"Markdown transport overrides") < raw.index(paragraph)


def test_out_of_scope_instructions_are_the_bytes_built_without_this_change(tmp_path):
    prepared = prepared_for(tmp_path, "credit_snapshot", "secondary", "executed")
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    in_scope = prepared_for(in_dir, "credit_snapshot", "secondary", "draft")
    paragraph = cpos_launch.PROVISIONAL_PARAGRAPH.encode()
    sentence = cpos_launch.CONSUMER_SENTENCE.encode()
    for module in prepared.ordered:
        removed = instructions_of(in_scope, module).replace(paragraph, b"")
        removed = removed.replace(sentence + b"\n\n", b"")
        assert instructions_of(prepared, module) == removed, module


def test_consumer_sentence_is_written_in_scope_even_without_cp4(tmp_path):
    modules = ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-5"]
    prepared = prepared_for(tmp_path, "credit_snapshot", "primary", "draft", modules)
    assert "CP-4" not in prepared.ordered
    assert cpos_launch.CONSUMER_SENTENCE.encode() in instructions_of(prepared, "CP-5")


def test_a_register_outside_findings_is_missing(tmp_path):
    case = next(c for c in CASES if c["id"] == "executed-only-no-labels")
    prepared = prepared_for(tmp_path, case["pathway"], case["run_type"], case["legal_documents"])
    raw = case_answer(case, prepared)
    start = raw.index("### Legal document register")
    end = raw.index("## Calculations")
    block = raw[start:end]
    moved = raw.replace(block, "").replace("## Calculations\n\n", "## Calculations\n\n" + block, 1)
    assert moved.index(block) > moved.index("## Calculations")
    task = HandoffTask(
        prepared.plan.run,
        "CP-4",
        instructions_of(prepared, "CP-4"),
        {"annual.txt": b"Net sales", "context": b"{}"},
        case_handoffs(case),
        1,
        (),
    )
    issues = _checked_handoff(task, moved.encode(), checker(prepared.layout))
    assert new_categories(issues) == {"register_missing"}, issues


def categories_for(tmp_path, register: str) -> set[str]:
    """The key's executed-only case with its register replaced: the rest of the answer is valid."""
    case = next(c for c in CASES if c["id"] == "executed-only-no-labels")
    prepared = prepared_for(tmp_path, case["pathway"], case["run_type"], case["legal_documents"])
    raw = case_answer({**case, "answer": {**case["answer"], "register": register}}, prepared)
    task = HandoffTask(
        prepared.plan.run,
        "CP-4",
        instructions_of(prepared, "CP-4"),
        {"annual.txt": b"Net sales", "context": b"{}"},
        case_handoffs(case),
        1,
        (),
    )
    return new_categories(_checked_handoff(task, raw.encode(), checker(prepared.layout)))


HEADER_ROW = "| Document | Kind | Status | Authority rank | Source |"
CA = "credit agreement or indenture"


def test_a_register_without_a_separator_row_is_missing_not_short_a_row(tmp_path):
    register = (
        f"{HEADER_ROW}\n| Draft CA | {CA} | draft | 1 | ca.htm |\n"
        f"| Old CA | {CA} | executed | 1 | old.htm |"
    )
    assert categories_for(tmp_path, register) == {"register_missing"}


def test_in_scope_a_register_of_only_other_rows_needs_the_blocked_line(tmp_path):
    register = (
        f"{HEADER_ROW}\n| --- | --- | --- | --- | --- |\n"
        "| 10-K | other | filed | not ranked | 10-k.htm |"
    )
    assert categories_for(tmp_path, register) == {"blocked_line_missing"}


def test_cp4_scope_is_decided_by_the_paragraph_alone(tmp_path):
    # Primary/draft run, but the task's instructions lack the paragraph: no new check applies.
    prepared = prepared_for(tmp_path, "credit_snapshot", "primary", "draft")
    task = HandoffTask(prepared.plan.run, "CP-4", b"no paragraph", {}, {}, 1, ())
    assert cpos_launch.cp4_issues(task, "## Findings\n", ()) == ()


ALLOWED_TOOLS = {
    "list_sources",
    "read_pages",
    "search_source",
    "calculate",
    "write_handoff",
    "edit_handoff",
    "score_governance",
}


@pytest.mark.parametrize("config", sorted(CONFIGS))
def test_no_provider_request_passes_a_tool_that_can_reach_the_internet(config):
    """C1n: an app run reads only the pinned sources, so it cannot fetch EDGAR."""
    if CONFIGS[config].provider == "copilot":
        pytest.skip("Copilot is not an https request body")
    spec = ModelSpec(
        config, CONFIGS[config].provider, CONFIGS[config].model, CONFIGS[config].effort
    )
    request = TurnRequest((Message("system", "s"), Message("user", "u")), TOOLS, 1000, spec.effort)
    body = json.loads(build(spec, request, "not-a-real-key").body)
    names = {t.get("name") or t["function"]["name"] for t in body["tools"]}
    assert names == {t.name for t in TOOLS} <= ALLOWED_TOOLS
    assert not re.search(
        r"web_search|web_fetch|browse|fetch_url|edgar", json.dumps(body["tools"]), re.IGNORECASE
    )


def test_every_handoff_request_in_the_loop_carries_exactly_the_fixed_tools():
    source = (ROOT / "src/deploy_workflow/model/handoff.py").read_text()
    calls = [m.start() for m in re.finditer(r"TurnRequest\(", source)]
    assert calls
    for start in calls:
        assert "TOOLS," in source[start : start + 120]
