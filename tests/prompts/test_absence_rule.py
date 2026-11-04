"""CP1H-R23 (T18): the composer states the source_context absence rule the gate enforces."""

import pytest
from prompt_support import request_for

from deploy_vii.live.prompts import STEP_CONTRACTS
from deploy_vii.preparation import PreparedPack
from deploy_workflow.prompts import rules
from deploy_workflow.prompts.absence_rule import ABSENCE_RULE_ID, ABSENCE_STATEMENT
from deploy_workflow.prompts.compose import compose

FROZEN_STATEMENT = (
    "Before you set a source's `event_scan` to `no_events_identified`, run `search_pack` over "
    "that source in this step; reading its pages does not count."
)


def test_the_absence_line_sits_once_immediately_before_rules(pack: PreparedPack) -> None:
    system = compose(request_for("source_context", pack))[0].text
    line = f"[source_context.absence] {FROZEN_STATEMENT}\n"
    assert system.count(line) == 1
    after = system.split(line, 1)[1]
    assert after.splitlines()[0] == "Rules:"


@pytest.mark.parametrize("step_id", sorted(s for s in STEP_CONTRACTS if s != "source_context"))
def test_no_other_step_states_the_absence_rule(pack: PreparedPack, step_id: str) -> None:
    assert "source_context.absence" not in compose(request_for(step_id, pack))[0].text


def test_the_rule_list_holds_the_absence_rule() -> None:
    by_id = {r.id: r for r in rules.load_rules("source_context")}
    rule = by_id["source_context.absence"]
    assert rule.statement == FROZEN_STATEMENT
    assert "fn:deploy_vii.live.tools:absence_issues" in rule.checks
    assert list(by_id)[-1] == "source_context.absence"


def test_the_statement_is_the_frozen_text() -> None:
    assert ABSENCE_RULE_ID == "source_context.absence"
    assert ABSENCE_STATEMENT == FROZEN_STATEMENT
