"""Undo the CP1H-R22 rule line in CP-3's composed message: the line
``[financials.coverage] <statement>`` that sits before ``Rules:`` in every composed financials
message. Removing exactly this line gives the message the digest pinned in OLD_FROZEN."""

from deploy_workflow.prompts.coverage_rule import COVERAGE_RULE_ID, COVERAGE_STATEMENT

COVERAGE_LINE = f"[{COVERAGE_RULE_ID}] {COVERAGE_STATEMENT}\n"


def undo_coverage(step_id: str, text: str) -> str:
    """Remove the coverage line from a composed message (financials only)."""
    if step_id != "financials":
        return text
    assert text.count(COVERAGE_LINE) == 1, step_id
    return text.replace(COVERAGE_LINE, "")
