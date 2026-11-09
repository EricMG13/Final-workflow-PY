"""Undo the S06-A06 words in CP-2's composed message (`credit_synthesis` only): rule b
(`CP2_SIGNALS_RULE`) now says a Critical signal is restated by a gaps row of severity Critical.
Removing exactly that clause gives the message the frozen digests pinned before the fix."""

S06_CLAUSE = ", of severity Critical when the signal's status is Critical"


def undo_s06(step_id: str, text: str) -> str:
    """Remove the S06-A06 clause from rule b of a composed CP-2 message."""
    if step_id != "credit_synthesis":
        return text
    assert text.count(S06_CLAUSE) == 1, step_id
    return text.replace(S06_CLAUSE, "")
