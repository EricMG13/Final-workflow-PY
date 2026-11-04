"""CP1H-R22 (T17): the composer states the financials coverage rule the T16 gate enforces."""

import pytest
from prompt_support import request_for

from deploy_vii.live.prompts import STEP_CONTRACTS
from deploy_vii.preparation import PreparedPack
from deploy_workflow.prompts import rules
from deploy_workflow.prompts.compose import compose
from deploy_workflow.prompts.coverage_rule import COVERAGE_RULE_ID, COVERAGE_STATEMENT

FROZEN_STATEMENT = (
    "Map every statement unit `extract_statements` returns in `unit_maps`; Python then writes "
    "its statement lines from the extracted text. For each unit give its `source_id` and "
    "`locator`, the `book_id`, the `statement` (BS, IS or CFS; comprehensive income is IS), "
    "`columns` with one period_id from that book per printed column, or null when the book "
    "declares no period for it or another unit already gives that period, and `rows` with "
    "each extracted row's number and its `line_id` (used once in its book), `item_id`, "
    "`line_kind` and `sign_convention` (total liabilities and equity is "
    "`other:total_liabilities_and_equity`). Do not write lines for the rows you map. Write a "
    "`statement_lines` entry only for a row Python leaves to you (the submit result's notes "
    "name each one): the row's statement, its label verbatim, each mapped column's amount (a "
    "printed dash is 0), citing the row's own locator (on a line source, `line:N` with N the "
    "row's number in the extract) with a quote that holds the row label. A row left uncovered "
    "is refused as an `Uncovered extracted statement line` with its reason."
)


def test_the_coverage_line_sits_once_immediately_before_rules(pack: PreparedPack) -> None:
    system = compose(request_for("financials", pack))[0].text
    line = f"[financials.coverage] {COVERAGE_STATEMENT}\n"
    assert system.count(line) == 1
    after = system.split(line, 1)[1]
    assert after.splitlines()[0] == "Rules:"


@pytest.mark.parametrize("step_id", sorted(s for s in STEP_CONTRACTS if s != "financials"))
def test_no_other_step_states_the_coverage_rule(pack: PreparedPack, step_id: str) -> None:
    assert "financials.coverage" not in compose(request_for(step_id, pack))[0].text


def test_the_rule_list_holds_the_coverage_rule() -> None:
    by_id = {r.id: r for r in rules.load_rules("financials")}
    rule = by_id["financials.coverage"]
    assert rule.statement == FROZEN_STATEMENT
    assert "fn:deploy_workflow.financial_workflow:_evidence_issues" in rule.checks
    assert list(by_id)[-1] == "financials.coverage"


def test_the_statement_is_the_frozen_text() -> None:
    assert COVERAGE_RULE_ID == "financials.coverage"
    assert COVERAGE_STATEMENT == FROZEN_STATEMENT
