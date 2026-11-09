"""Undo the S09-A05 sentence in CP-4's composed message (`legal_covenants` only): rule d
(`CP4_THRESHOLD_RULE`) gained one sentence on strict comparisons against inclusive wording.
Removing exactly that sentence and the space before it gives the message the frozen digests pinned
before the fix."""

S09_A05_SENTENCE = (
    " A strict comparison (`<`, `>`) is rejected when the quote words the limit only as "
    "inclusive (no more than, no greater than, no less than, or less, or more, at least, "
    "minimum, maximum, shall not permit ... to exceed), so write `<=` or `>=`."
)


def undo_s09_a05(step_id: str, text: str) -> str:
    """Remove the S09-A05 sentence from rule d of a composed CP-4 message."""
    if step_id != "legal_covenants":
        return text
    assert text.count(S09_A05_SENTENCE) == 1, step_id
    return text.replace(S09_A05_SENTENCE, "")
