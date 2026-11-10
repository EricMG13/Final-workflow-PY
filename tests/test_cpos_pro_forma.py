"""Task 11a: the Primary pro forma tables' instructions and structural checker. The cases are the
frozen answer key tests/fixtures/primary-pro-forma/checker-cases.json; the expected issue
categories are read from it, never computed here."""

import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_cpos_launch import answer
from test_cpos_provisional import instructions_of, prepared_for

from deploy_vii.contracts import PATHWAY_MODULES
from deploy_workflow.owners import cpos_launch
from deploy_workflow.owners.cpos import HandoffTask, _checked_handoff
from deploy_workflow.owners.cpos_launch import checker

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/primary-pro-forma/checker-cases.json").read_text())[
    "cases"
]
LOWS = json.loads((ROOT / "tests/fixtures/primary-pro-forma/checker-cases-lows.json").read_text())[
    "cases"
]
LOWS_R2 = json.loads(
    (ROOT / "tests/fixtures/primary-pro-forma/checker-cases-lows-r2.json").read_text()
)["cases"]
CONSTANTS = {"CP-1A": "PRO_FORMA_CP1A", "CP-1D": "PRO_FORMA_CP1D", "CP-2": "PRO_FORMA_CP2"}


def categories(issues: tuple[str, ...]) -> set[str]:
    found = set()
    for issue in issues:
        for category, prefix in cpos_launch.PRO_FORMA_ISSUES.items():
            if issue.startswith(prefix):
                found.add(category)
    return found


def case_answer(case: dict, prepared) -> str:
    module = case["module"]
    context = {
        "module_id": module,
        "sources": {"annual.txt": hashlib.sha256(b"Net sales").hexdigest()},
        "handoffs": {"CP-1": {"sha256": hashlib.sha256(b"# upstream").hexdigest()}},
    }
    text = answer(context, [r for r in prepared.plan.layout.routes if r.block_id != "pro-forma"])
    marker = "## Calculations"
    assert marker in text
    return text.replace(marker, case["findings"] + "\n\n" + marker, 1)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_checker_matches_the_frozen_answer_key(tmp_path, case):
    prepared = prepared_for(
        tmp_path, case["pathway"], case["run_type"], "executed", [case["module"]]
    )
    raw = case_answer(case, prepared)
    task = HandoffTask(
        prepared.plan.run,
        case["module"],
        instructions_of(prepared, case["module"]),
        {"annual.txt": b"Net sales", "context": b"{}"},
        {"CP-1": b"# upstream"},
        1,
        (),
    )
    issues = _checked_handoff(task, raw.encode(), checker(prepared.layout))
    assert categories(issues) == set(case["expected"]["issues"]), issues
    # The rest of the synthetic answer is valid, so acceptance is the key's verdict.
    assert (issues == ()) == case["expected"]["accepted"]


@pytest.mark.parametrize("module", sorted(CONSTANTS))
@pytest.mark.parametrize("run_type", ["primary", "secondary"])
def test_constant_is_in_instructions_only_on_primary_runs(tmp_path, module, run_type):
    prepared = prepared_for(tmp_path, "credit_snapshot", run_type, "executed", [module])
    constant = getattr(cpos_launch, CONSTANTS[module]).encode()
    assert (constant in instructions_of(prepared, module)) == (run_type == "primary")
    for other, name in CONSTANTS.items():
        if other != module:
            assert getattr(cpos_launch, name).encode() not in instructions_of(prepared, module)


@pytest.mark.parametrize("case", LOWS, ids=[c["id"] for c in LOWS])
def test_checker_matches_the_lows_answer_key(case):
    """Rulings R-L1 to R-L13 (frozen key checker-cases-lows.json). `wrap: false` findings are the
    whole answer; otherwise they sit under `## Findings`, as in the 80-case key."""
    text = case["findings"]
    if case.get("wrap", True):
        text = "## Findings\n\n" + text + "\n## Calculations\n\nnone\n"
    task = SimpleNamespace(instructions=cpos_launch.PRO_FORMA[case["module"]].encode())
    issues = cpos_launch.pro_forma_issues(task, text)
    assert categories(issues) == set(case["expected"]["issues"]), issues
    assert (issues == ()) == case["expected"]["accepted"]


def findings_text(case: dict) -> str:
    """`wrap: false` findings are the whole answer; otherwise they sit under `## Findings`."""
    text = case["findings"]
    if case.get("wrap", True):
        text = "## Findings\n\n" + text + "\n## Calculations\n\nnone\n"
    return text


@pytest.mark.parametrize("case", LOWS_R2, ids=[c["id"] for c in LOWS_R2])
def test_checker_matches_the_round_2_answer_key(case):
    """R-L9 (widened) and R-L14 to R-L18 (frozen key checker-cases-lows-r2.json)."""
    task = SimpleNamespace(instructions=cpos_launch.PRO_FORMA[case["module"]].encode())
    issues = cpos_launch.pro_forma_issues(task, findings_text(case))
    assert categories(issues) == set(case["expected"]["issues"]), issues
    assert (issues == ()) == case["expected"]["accepted"]


# Round 2 (lead condition as round 1): case id -> phrases that the instruction text and the issue
# message must both carry.
ROUND_2_RULES = {
    "r2-ut-fx-line-above-heading": ["under the heading, above the table"],
    "r2-tr-fx-line-after-table": ["under the heading, above the table"],
    "r2-ut-fx-no-parens": ["FX rate: <rate> (<source>)", "AAA/BBB"],
    "r2-ut-plus-sign": ["with no plus sign"],
    "r2-ut-bare-leading-point": ["with no plus sign"],
    "r2-ut-comma-after-4-digits": ["one to three digits"],
    "r2-ut-total-debt-usd-lowercase": ["exactly as shown"],
    "r2-ut-total-debt-capital-d": ["exactly as shown"],
    "r2-tr-two-findings-headings": ["one `## Findings` section"],
    "r2-ut-findings-heading-colon": ["exactly as shown", "`## Findings`"],
}


@pytest.mark.parametrize("case_id", sorted(ROUND_2_RULES))
def test_each_round_2_rule_is_in_the_instructions_and_named_in_the_message(case_id):
    case = next(c for c in LOWS_R2 if c["id"] == case_id)
    constant = cpos_launch.PRO_FORMA[case["module"]]
    issues = cpos_launch.pro_forma_issues(
        SimpleNamespace(instructions=constant.encode()), findings_text(case)
    )
    for phrase in ROUND_2_RULES[case_id]:
        assert any(phrase in issue for issue in issues), (phrase, issues)
        assert phrase in constant, phrase


# Each module's rejecting label rule is told in that module's own instruction (R-L17 condition),
# and the issue message quotes the expected label. Bodies are the 80-case key's valid tables.
INEXACT_LABELS = {
    "CP-1A": ("cp1a-sources-uses-valid-user-entered", "| Total sources |", "| Total Sources |"),
    "CP-1D": ("cp1d-register-valid", "| Rejected |", "| rejected |"),
}


@pytest.mark.parametrize("module", sorted(CONSTANTS))
def test_every_module_tells_labels_are_exact_and_the_heading_message_quotes_it(module):
    constant = cpos_launch.PRO_FORMA[module]
    assert "exactly as shown" in constant
    body = next(c for c in CASES if c["module"] == module and c["expected"]["accepted"])
    text = "## Findings:\n\n" + body["findings"] + "\n## Calculations\n\nnone\n"
    issues = cpos_launch.pro_forma_issues(SimpleNamespace(instructions=constant.encode()), text)
    assert any("`## Findings`" in issue for issue in issues), issues


@pytest.mark.parametrize("module", sorted(INEXACT_LABELS))
def test_an_inexact_row_label_is_rejected_by_the_module_that_told_it(module):
    key, exact, inexact = INEXACT_LABELS[module]
    findings = next(c for c in CASES if c["id"] == key)["findings"]
    assert exact in findings
    constant = cpos_launch.PRO_FORMA[module]
    text = "## Findings\n\n" + findings.replace(exact, inexact) + "\n## Calculations\n\nnone\n"
    issues = cpos_launch.pro_forma_issues(SimpleNamespace(instructions=constant.encode()), text)
    assert issues, "an inexact label must be rejected"
    assert "exactly as shown" in constant


def test_nested_emphasis_is_read_in_bounded_time():
    line = "*" * 16000 + "x" + "*" * 16000
    start = time.perf_counter()
    cpos_launch._plain(line)
    assert time.perf_counter() - start < 1.0
    assert cpos_launch._plain("**_x_**") == "x"


def test_a_rejected_total_label_quotes_the_expected_label():
    for case_id in ("r2-ut-total-debt-usd-lowercase", "r2-ut-total-debt-capital-d"):
        case = next(c for c in LOWS_R2 if c["id"] == case_id)
        task = SimpleNamespace(instructions=cpos_launch.PRO_FORMA_CP2.encode())
        issues = cpos_launch.pro_forma_issues(task, findings_text(case))
        assert any("`Total debt (USD)`" in issue for issue in issues), issues


# Lead condition: a rejecting rule is told to the model in the Primary instruction text and named in
# the issue message, so no paid run is charged a repair turn for a rule it was never told. Each
# phrase must be in both.
REJECTING_RULES = {
    "low-fp-su-outside-findings": "outside `## Findings`",
    "low-fp-fx-line-after-table": "a line after the table does not count",
    "low-fp-cap-cash-only": "at least one debt row",
    "low-fp-cap-total-usd-currency-eur": "Currency must equal the code in the label",
    "low-fp-cap-total-gbp-no-gbp-debt": "no debt row uses",
    "low-fp-cell-decimal-comma-8,3": "exactly three digits",
    "low-fp-cell-commas-1,,,": "exactly three digits",
    "low-fp-cell-not-supplied-dash": "at least one letter or digit",
    "low-ff-unicode-minus": "ASCII",
}


@pytest.mark.parametrize("case_id", sorted(REJECTING_RULES))
def test_each_rejecting_rule_is_in_the_instructions_and_named_in_the_message(case_id):
    case = next(c for c in LOWS if c["id"] == case_id)
    phrase = REJECTING_RULES[case_id]
    text = case["findings"]
    if case.get("wrap", True):
        text = "## Findings\n\n" + text + "\n## Calculations\n\nnone\n"
    constant = cpos_launch.PRO_FORMA[case["module"]]
    issues = cpos_launch.pro_forma_issues(SimpleNamespace(instructions=constant.encode()), text)
    assert any(phrase in issue for issue in issues), issues
    assert phrase in constant


# sha256 over every instruction file of every non-Primary-affected run (all pathways, both run
# types, executed and draft legal documents, four module selections), the module order of every
# Secondary run, and each refusal. Computed from the base tree (01f0efe4) by the same function,
# never from this tree: a Primary run's CP-1A, CP-1D and CP-2 files are the only bytes that may
# move.
BASE_NON_PRIMARY_DIGEST = "d0bf5a8a3fa0627a8cf3a3a7a5f9a993cc57355cc4e5e5d4b4535777f5b73142"


def non_primary_digest(root: Path) -> str:
    entries = []
    count = 0
    for pathway in sorted(PATHWAY_MODULES):
        for run_type in ("secondary", "primary"):
            for legal in ("executed", "draft"):
                for modules in (None, ["CP-1A"], ["CP-2"], ["CP-1D"]):
                    key = f"{pathway}|{run_type}|{legal}|{modules}"
                    count += 1
                    folder = root / str(count)
                    folder.mkdir()
                    try:
                        prepared = prepared_for(folder, pathway, run_type, legal, modules)
                    except cpos_launch.LaunchRefused as refusal:
                        entries.append((key, "refused", f"{type(refusal).__name__}: {refusal}"))
                        continue
                    if run_type == "secondary":
                        entries.append((key, "ordered", ",".join(prepared.ordered)))
                    for file in sorted((prepared.directory / "instructions").glob("*.md")):
                        if run_type == "primary" and file.stem in CONSTANTS:
                            continue
                        entries.append(
                            (key, file.name, hashlib.sha256(file.read_bytes()).hexdigest())
                        )
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()


def test_non_primary_instruction_bytes_are_those_of_the_base_tree(tmp_path):
    assert non_primary_digest(tmp_path) == BASE_NON_PRIMARY_DIGEST


def test_secondary_instructions_hold_no_pro_forma_text(tmp_path):
    prepared = prepared_for(tmp_path, "credit_snapshot", "secondary", "executed", ["CP-2"])
    raw = instructions_of(prepared, "CP-2")
    for name in CONSTANTS.values():
        assert getattr(cpos_launch, name).encode() not in raw
    assert b"Pro forma" not in raw


def test_constants_carry_the_contract_text():
    assert "| Side | Item | Amount | Currency | Basis | Source |" in cpos_launch.PRO_FORMA_CP1A
    assert "`user-entered`" in cpos_launch.PRO_FORMA_CP1A
    assert "### Add-back LTM register" in cpos_launch.PRO_FORMA_CP1D
    two = cpos_launch.PRO_FORMA_CP2
    for text in ("### Pro forma capitalisation", "### EBITDA ladder", "### Pro forma leverage"):
        assert text in two
    assert "`calculate`" in two and "leading minus" in two


def test_primary_defaults_add_cp1d_and_secondary_does_not(tmp_path):
    primary = prepared_for(tmp_path, "credit_snapshot", "primary", "executed")
    assert "CP-1D" in primary.plan.run.requested_modules
    assert primary.ordered.index("CP-1D") < primary.ordered.index("CP-2")
    (tmp_path / "s").mkdir()
    secondary = prepared_for(tmp_path / "s", "credit_snapshot", "secondary", "executed")
    assert "CP-1D" not in secondary.plan.run.requested_modules


def test_explicit_module_list_is_taken_as_given(tmp_path):
    prepared = prepared_for(tmp_path, "credit_snapshot", "primary", "executed", ["CP-2"])
    assert "CP-1D" not in prepared.plan.run.requested_modules


FENCES = json.loads((ROOT / "tests/fixtures/primary-pro-forma/fence-cases.json").read_text())[
    "cases"
]
FENCE_RULE = "Fenced code under `## Findings` is not read."


def fence_instructions(case: dict) -> bytes:
    """A case on a non-Primary run is checked by instructions that carry no pro forma constant."""
    if case["id"] == "fence-f12-non-primary-no-check":
        return b"Method."
    return cpos_launch.PRO_FORMA[case["module"]].encode()


@pytest.mark.parametrize("case", FENCES, ids=[c["id"] for c in FENCES])
def test_checker_matches_the_fence_answer_key(case):
    """R-L19 (frozen key fence-cases.json): fenced code under `## Findings` is not read."""
    issues = cpos_launch.pro_forma_issues(
        SimpleNamespace(instructions=fence_instructions(case)), findings_text(case)
    )
    assert categories(issues) == set(case["expected"]["issues"]), issues
    assert (issues == ()) == case["expected"]["accepted"]


@pytest.mark.parametrize("module", sorted(CONSTANTS))
def test_the_fence_rule_is_told_in_every_primary_instruction(module):
    assert FENCE_RULE in cpos_launch.PRO_FORMA[module]


def test_an_accepted_cp2_fence_case_delivers_the_key_block_without_the_fenced_copy(tmp_path):
    """Checker/delivery agreement: what the checker accepts delivers the unfenced table only."""
    from test_cpos_pro_forma_delivery import CP2_RUN, PROSE, TAIL, deliver

    from deploy_vii.report_view import ReportView

    delivered = json.loads(
        (ROOT / "tests/fixtures/primary-pro-forma/delivered-block.json").read_text()
    )["pro-forma"]
    case = next(c for c in FENCES if c["id"] == "fence-f9-cp2-fenced-capitalisation-example")
    assert case["expected"]["accepted"]
    head = "# CP-2 Acme Corp\n\n## Request\nAcme Corp pro forma.\n\n## Sources\nsrc.pdf\n\n"
    text = head + "## Findings\n\n" + PROSE + case["findings"] + "\n\n" + TAIL
    files = deliver(tmp_path, CP2_RUN, "CP-2", text, "primary")
    block = next(
        b
        for b in ReportView.model_validate_json(files["report-view.json"]).blocks
        if b.block_id == "pro-forma"
    )
    for table, key in (
        (block, delivered["capitalisation"]),
        (block.tabs[0], delivered["leverage"]),
    ):
        assert [table.row_header, *table.columns] == key["header"]
        assert [[r.label, *(c.text for c in r.cells)] for r in table.rows] == key["rows"]


def test_lone_cr_line_endings_are_read_as_line_breaks():
    """Delivery's `physical_lines` splits on a lone CR, so the checker must read it too."""
    case = next(c for c in CASES if c["id"] == "cp2-full-valid")
    text = findings_text(case).replace("\n", "\r")
    task = SimpleNamespace(instructions=cpos_launch.PRO_FORMA["CP-2"].encode())
    assert cpos_launch.pro_forma_issues(task, text) == ()
