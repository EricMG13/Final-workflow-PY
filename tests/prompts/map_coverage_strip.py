"""Undo the CP1H-R23 (T21c) map coverage rule in the financials composed message: the line
``[financials.coverage] <statement>`` now tells the model to map every unit in ``unit_maps``.
Putting the R22.1 line back gives the message the digest pinned in PRE_MAP_COVERAGE_FROZEN (the
T21b FROZEN value). The R22.1 statement is a literal here, copied from ``COVERAGE_STATEMENT`` at
7f13ad80, so the strip does not move with the rule."""

from deploy_workflow.prompts.coverage_rule import COVERAGE_RULE_ID, COVERAGE_STATEMENT

R22_STATEMENT = (
    "Cover every row `extract_statements` returns. Each row needs at least one column whose "
    "period your book declares, and for each such column one statement line with the row's "
    "statement, its label verbatim and that column's amount (a printed dash is 0), citing the "
    "row's own locator (on a line source, `line:N` with N the row's number in the extract, "
    "not the table's range) with a quote that holds the row label. A row left uncovered is "
    "refused as an `Uncovered extracted statement line` with its reason."
)
NEW_LINE = f"[{COVERAGE_RULE_ID}] {COVERAGE_STATEMENT}\n"
OLD_LINE = f"[{COVERAGE_RULE_ID}] {R22_STATEMENT}\n"


def undo_map_coverage(step_id: str, text: str) -> str:
    """Put the R22.1 coverage line back in a composed message (financials only)."""
    if step_id != "financials":
        return text
    assert text.count(NEW_LINE) == 1, step_id
    return text.replace(NEW_LINE, OLD_LINE)
