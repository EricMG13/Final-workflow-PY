"""Undo the S09-A07 wording in CP-5's composed message (`integrity_review` only): rule b
(`CP5_REVIEW_RULE`) now says that a supported or partly_supported verdict names at least one
reference that belongs to the claim. Removing exactly that clause gives the message the frozen
digests pinned before the fix."""

S09_A07_CLAUSE = (
    " that belongs to that claim (one of its own citation refs, a fact its text names or a fact "
    "filed under its id)"
)


def undo_s09_a07(step_id: str, text: str) -> str:
    """Remove the S09-A07 clause from rule b of a composed CP-5 message."""
    if step_id != "integrity_review":
        return text
    assert text.count(S09_A07_CLAUSE) == 1, step_id
    return text.replace(S09_A07_CLAUSE, "")
