"""Undo the CP1H-R23 rule line in CP-1's composed message: the line
``[source_context.absence] <statement>`` that sits before ``Rules:`` in every composed
source_context message. Removing exactly this line gives the message the digest pinned in
PRE_ABSENCE_FROZEN."""

from deploy_workflow.prompts.absence_rule import ABSENCE_RULE_ID, ABSENCE_STATEMENT

ABSENCE_LINE = f"[{ABSENCE_RULE_ID}] {ABSENCE_STATEMENT}\n"


def undo_absence(step_id: str, text: str) -> str:
    """Remove the absence line from a composed message (source_context only)."""
    if step_id != "source_context":
        return text
    assert text.count(ABSENCE_LINE) == 1, step_id
    return text.replace(ABSENCE_LINE, "")
