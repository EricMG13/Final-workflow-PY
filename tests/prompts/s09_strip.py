"""Undo the S09-A02/A03 sentence in CP-4's composed message (`legal_covenants` only): rule d
(`CP4_THRESHOLD_RULE`) gained one sentence on the governing-document quote and step-down
schedules. Removing exactly that sentence and the space before it gives the message the frozen
digests pinned before the fix."""

S09_SENTENCE = (
    " The quote that holds it is one of the covenant's governing document (`document_id`) and "
    "writes that number as a threshold, not inside a longer number; when that quote or its "
    "sentence states another threshold of the unit (a step-down schedule or several tests), "
    "`threshold_unit` is other."
)


def undo_s09(step_id: str, text: str) -> str:
    """Remove the S09 sentence from rule d of a composed CP-4 message."""
    if step_id != "legal_covenants":
        return text
    assert text.count(S09_SENTENCE) == 1, step_id
    return text.replace(S09_SENTENCE, "")
