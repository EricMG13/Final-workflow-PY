"""Undo the S13-A07 wording in the narrative rule c (`narrative` only): NARRATIVE_COVERAGE_RULE
now adds that, under `financial_synthesis`, a financial dimension the `financial_dimensions` line
leaves out takes no finding either. Removing the sentence gives the message the frozen digests
pinned before the fix."""

R_NARR_NEW = (
    " Under `financial_synthesis`, a financial dimension the `financial_dimensions` line leaves "
    "out takes no finding either."
)


def undo_r_narr(step_id: str, text: str) -> str:
    """Restore the pre-fix end of rule c in a composed narrative message."""
    if R_NARR_NEW not in text:
        assert step_id != "narrative", step_id
        return text
    assert step_id == "narrative" and text.count(R_NARR_NEW) == 1, step_id
    return text.replace(R_NARR_NEW, "")
