"""Task 11a: the Primary pro forma tables' instructions and structural checker. The cases are the
frozen answer key tests/fixtures/primary-pro-forma/checker-cases.json; the expected issue
categories are read from it, never computed here."""

import hashlib
import json
from pathlib import Path

import pytest
from test_cpos_launch import answer
from test_cpos_provisional import instructions_of, prepared_for

from deploy_workflow.owners import cpos_launch
from deploy_workflow.owners.cpos import HandoffTask, _checked_handoff
from deploy_workflow.owners.cpos_launch import checker

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/primary-pro-forma/checker-cases.json").read_text())[
    "cases"
]
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
    text = answer(context, list(prepared.plan.layout.routes))
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


def test_secondary_instructions_are_byte_for_byte_the_old_ones(tmp_path):
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
