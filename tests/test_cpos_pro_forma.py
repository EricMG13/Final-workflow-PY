"""Task 11a: the Primary pro forma tables' instructions and structural checker. The cases are the
frozen answer key tests/fixtures/primary-pro-forma/checker-cases.json; the expected issue
categories are read from it, never computed here."""

import hashlib
import json
import re
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
RC2_DIR = ROOT / "tests/fixtures/primary-pro-forma/rc2"
RC2 = json.loads((RC2_DIR / "checker-cases-rc2.json").read_text())["cases"]
# R-C2-1 supersedes the expected result of exactly four round-2 cases (lead ruling A4 (a),
# 2026-11-10): each holds `Not supplied` in a Source row and a `Total sources` row. The round-2
# key file is not edited; the override is applied here, by id.
SUPERSEDED = {
    s["id"]: s for s in json.loads((RC2_DIR / "superseded.json").read_text())["superseded"]
}
INSTRUCTION_TEXT = json.loads((RC2_DIR / "instruction-text.json").read_text())
SUBSTITUTIONS = json.loads((RC2_DIR / "substitutions.json").read_text())


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
    expected = round_2_expected(case)
    task = SimpleNamespace(instructions=cpos_launch.PRO_FORMA[case["module"]].encode())
    issues = cpos_launch.pro_forma_issues(task, findings_text(case))
    assert categories(issues) == set(expected["issues"]), issues
    assert (issues == ()) == expected["accepted"]


def round_2_expected(case: dict) -> dict:
    """The key's expected result, except for the four ids R-C2-1 supersedes (ruling A4 (a))."""
    override = SUPERSEDED.get(case["id"])
    if override is None:
        return case["expected"]
    assert case["expected"] == override["old_expected"], case["id"]
    assert "A4 (a)" in override["citation"] and "R-C2-1" in override["citation"]
    return override["new_expected"]


def test_exactly_four_round_2_cases_are_superseded_by_r_c2_1():
    assert sorted(SUPERSEDED) == [
        "r2-ma-ns-10k",
        "r2-ma-ns-e-acute",
        "r2-ma-ns-na",
        "r2-ma-ns-nonascii-dash-letters",
    ]
    assert set(SUPERSEDED) <= {c["id"] for c in LOWS_R2}
    for case_id in SUPERSEDED:  # Each is rejected for its total, which is what R-C2-1 changes.
        case = next(c for c in LOWS_R2 if c["id"] == case_id)
        assert "Not supplied:" in case["findings"] and "Total sources" in case["findings"]


@pytest.mark.parametrize("case", RC2, ids=[c["id"] for c in RC2])
def test_checker_matches_the_rc2_answer_key(case):
    """R-C2-1 (frozen key rc2/checker-cases-rc2.json): Memo commitments; a total only when every
    row of its side holds a number."""
    task = SimpleNamespace(instructions=cpos_launch.PRO_FORMA[case["module"]].encode())
    issues = cpos_launch.pro_forma_issues(task, findings_text(case))
    assert categories(issues) == set(case["expected"]["issues"]), issues
    assert (issues == ()) == case["expected"]["accepted"]


RC2_R1 = json.loads((RC2_DIR / "checker-cases-rc2-r1.json").read_text())["cases"]


@pytest.mark.parametrize("case", RC2_R1, ids=[c["id"] for c in RC2_R1])
def test_checker_matches_the_rc2_r1_answer_key(case):
    """Lead review of #84, fix round 1 (frozen key rc2/checker-cases-rc2-r1.json): every Item
    containing "total" is a total row and must be exact on its own Side; `(commitment)` only on a
    Memo row; a side of numbers carries a numeric total."""
    task = SimpleNamespace(instructions=cpos_launch.PRO_FORMA_CP1A.encode())
    issues = cpos_launch.pro_forma_issues(task, findings_text(case))
    assert categories(issues) == set(case["expected"]["issues"]), issues
    assert (issues == ()) == case["expected"]["accepted"]


@pytest.mark.parametrize(
    ("case_id", "phrase"),
    [
        ("rc2r1-subtotal-sources-an", 'containing "total"'),
        ("rc2r1-memo-item-has-total-an", 'containing "total"'),
        ("rc2r1-commitment-on-source-row-an", "belongs only on a Memo row"),
        ("rc2r1-not-supplied-total-on-all-number-side", "write the total as a number"),
    ],
)
def test_each_rc2_r1_refusal_names_its_rule(case_id, phrase):
    case = next(c for c in RC2_R1 if c["id"] == case_id)
    task = SimpleNamespace(instructions=cpos_launch.PRO_FORMA_CP1A.encode())
    issues = cpos_launch.pro_forma_issues(task, findings_text(case))
    assert any(phrase in issue for issue in issues), issues


def test_the_r1_key_supersedes_no_earlier_case():
    assert json.loads((RC2_DIR / "superseded-r1.json").read_text())["superseded"] == []


def test_a_memo_row_without_commitment_in_its_item_is_a_cell_error():
    """Controller ruling u9: the Item of a Memo row ends with `(commitment)`."""
    case = next(c for c in RC2 if c["id"] == "rc2-memo-funded-rows-both-totals")
    findings = case["findings"].replace("ABL facility size (commitment)", "ABL facility size")
    task = SimpleNamespace(instructions=cpos_launch.PRO_FORMA_CP1A.encode())
    issues = cpos_launch.pro_forma_issues(task, findings_text({**case, "findings": findings}))
    assert categories(issues) == {"pro_forma_cell"}, issues
    assert any("(commitment)" in issue for issue in issues), issues


def test_a_memo_amount_may_be_not_supplied_and_stays_out_of_the_totals():
    """Controller ruling u8: a Memo Amount follows the shared cell rule."""
    case = next(c for c in RC2 if c["id"] == "rc2-memo-funded-rows-both-totals")
    findings = case["findings"].replace(
        "| Memo | ABL facility size (commitment) | 125 |",
        "| Memo | ABL facility size (commitment) | Not supplied: no size entered |",
    )
    task = SimpleNamespace(instructions=cpos_launch.PRO_FORMA_CP1A.encode())
    assert cpos_launch.pro_forma_issues(task, findings_text({**case, "findings": findings})) == ()


def test_the_r1_instruction_sentence_is_the_keys_text():
    """Lead review of #84, r1: the three new refusals are stated in PRO_FORMA_CP1A (key
    rc2/instruction-text-r1.json). The key's `old` text is the start of its `new` text, so the
    bare `old` is found only inside it."""
    part = json.loads((RC2_DIR / "instruction-text-r1.json").read_text())
    constant = cpos_launch.PRO_FORMA_CP1A
    assert part["new"] in constant
    assert part["old"] not in constant.replace(part["new"], "")
    assert constant.count(part["new"]) == 1


def test_the_instruction_text_is_the_keys_text():
    """R-C2-1 and R-C2-7 sentences are inserted verbatim (rc2/instruction-text.json)."""
    for part in INSTRUCTION_TEXT["R-C2-1"]["replacements"]:
        assert part["old"] not in cpos_launch.PRO_FORMA_CP1A, part["old"]
        assert part["new"] in cpos_launch.PRO_FORMA_CP1A, part["new"]
    sentence = INSTRUCTION_TEXT["R-C2-7"]["sentence"]
    assert sentence in cpos_launch.PRO_FORMA_CELL_RULE
    for name in CONSTANTS.values():
        assert sentence in getattr(cpos_launch, name)


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
# move. R-C2-3, -6 and -7 move more bytes (lead ruling B1, 2026-11-10): the digest stays the base
# tree's, and each file is compared after the key's sentence substitutions
# (rc2/substitutions.json) are taken back out, so base bytes + exactly those substitutions == the
# new bytes. Nothing here is computed from production code except the bytes under test. A module
# outside the key's sets whose bytes move changes the digest and fails. R-26 (lead ruling
# R-SB4-plan-4-rulings.md, 2026-11-10) entries apply only where the chart bullet exists.
BASE_NON_PRIMARY_DIGEST = "d0bf5a8a3fa0627a8cf3a3a7a5f9a993cc57355cc4e5e5d4b4535777f5b73142"


def base_bytes(module: str, raw: bytes) -> bytes:
    """The file with the key's non-Primary substitutions for its module taken back out."""
    for part in reversed(SUBSTITUTIONS["non_primary"].get(module, [])):
        new, old = part["new"].encode(), part["old"].encode()
        if part.get("where_present") and new not in raw:
            assert old not in raw, (module, part["rule"])  # base text left un-substituted
            continue
        assert raw.count(new) == 1, (module, part["rule"])
        assert old not in raw, (module, part["rule"])
        raw = raw.replace(new, old)
    return raw


def test_where_present_cannot_hide_a_missing_insertion(tmp_path):
    prepared = prepared_for(tmp_path, "covenant_refinancing", "secondary", "executed", ["CP-1"])
    composed = instructions_of(prepared, "CP-1")
    r26 = [p for p in SUBSTITUTIONS["non_primary"]["CP-1"] if p["rule"] == "R-26"]
    assert len(r26) == 3 and not any(p["new"].encode() in composed for p in r26)
    assert base_bytes("CP-1", composed)  # neither old nor new: passes through
    leverage = r26[0]
    with pytest.raises(AssertionError):
        base_bytes("CP-1", composed + leverage["old"].encode())


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
                        raw = base_bytes(file.stem, file.read_bytes())
                        entries.append((key, file.name, hashlib.sha256(raw).hexdigest()))
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()


def test_non_primary_instruction_bytes_are_the_base_bytes_plus_the_keys_substitutions(tmp_path):
    assert non_primary_digest(tmp_path) == BASE_NON_PRIMARY_DIGEST


def rules_of(module: str) -> set[str]:
    return {part["rule"] for part in SUBSTITUTIONS["non_primary"][module]}


def test_the_key_lists_the_modules_it_changes():
    assert set(SUBSTITUTIONS["non_primary"]) == set(cpos_launch.METHODS)  # 20 modules
    by_rule = {
        rule: {m for m in SUBSTITUTIONS["non_primary"] if rule in rules_of(m)}
        for rule in ("R-C2-3", "R-C2-6", "R-C2-7")
    }
    assert len(by_rule["R-C2-6"]) == 20
    assert len(by_rule["R-C2-3"]) == 14
    assert by_rule["R-C2-7"] == {"CP-1"}
    assert by_rule["R-C2-3"] == set(
        INSTRUCTION_TEXT["R-C2-3"]["modules_naming_unavailable_scripts"]
    )


def test_r_c2_3_modules_are_those_whose_method_files_name_a_script():
    """The R-C2-3 sentence is composed for the modules whose method text names a script, and for
    no other."""
    pattern = re.compile(r"[\w./-]+\.(?:py|sh)\b")
    named = set()
    for module, files in cpos_launch.METHODS.items():
        text = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in files)
        if module == "CP-1":
            text += "\n".join(cpos_launch.STEP_CONTRACTS[step] for step in cpos_launch.CP1_STEPS)
        if pattern.search(text):
            named.add(module)
    assert named == set(INSTRUCTION_TEXT["R-C2-3"]["modules_naming_unavailable_scripts"])


@pytest.mark.parametrize("run_type", ["primary", "secondary"])
def test_each_substitution_is_in_the_instruction_exactly_once(tmp_path, run_type):
    prepared = prepared_for(tmp_path, "credit_snapshot", run_type, "executed", ["CP-0", "CP-1"])
    for module in ("CP-0", "CP-1"):
        raw = instructions_of(prepared, module)
        for part in SUBSTITUTIONS["non_primary"][module]:
            assert raw.count(part["new"].encode()) == 1, (module, part["rule"])
            assert part["old"].encode() not in raw


def test_the_primary_constants_carry_the_keys_additions(tmp_path):
    prepared = prepared_for(tmp_path, "credit_snapshot", "primary", "executed", ["CP-1A"])
    raw = instructions_of(prepared, "CP-1A")
    for part in [
        *SUBSTITUTIONS["primary_additions"]["CP-1A"],
        *SUBSTITUTIONS["non_primary"]["CP-1A"],
    ]:
        assert raw.count(part["new"].encode()) == 1, part["rule"]
        # An `old` that is the start of its `new` (R-C2-7) is only found inside it.
        assert part["old"].encode() not in raw.replace(part["new"].encode(), b""), part["rule"]
    for module in ("CP-1D", "CP-2"):
        constant = getattr(cpos_launch, CONSTANTS[module])
        for part in SUBSTITUTIONS["primary_additions"][module]:
            assert part["new"] in constant


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
