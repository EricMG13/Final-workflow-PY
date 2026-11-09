"""Undo the S09-cp4-cp5 rule sentences in composed messages. Removing exactly each sentence and
the space before it gives the message the frozen digests pinned before the rulings.

A08 (`legal_covenants`): rule e (`CP4_METRIC_RULE`) gained one sentence naming the refusal of
`Same definition` when a quote says the term is defined in a document that is not in the pack.
A04 (`restructuring_fulcrum`): rule b gained one sentence naming the refusal when CP-1 T4.18 shows
no single secured facility."""

R_CP4_SENTENCE = (
    " `metric_basis` is also Not determinable, never Same definition, when a quote of the "
    "covenant says the term is defined in a named agreement, indenture or other instrument that "
    "is not a SOURCE block of this run: Python refuses Same definition there."
)

R_CP4C_SENTENCE = (
    " The secured facility is the one facility CP-1 T4.18 shows as secured at its current "
    "quarter; when CP-1 shows none or more than one, Python refuses the step and names the count."
)
_SENTENCES = {"legal_covenants": R_CP4_SENTENCE, "restructuring_fulcrum": R_CP4C_SENTENCE}


def undo_r_cp4(step_id: str, text: str) -> str:
    """Remove the A08 sentence from rule e of a composed CP-4 message and the A04 sentence from
    rule b of a composed CP-4C message."""
    sentence = _SENTENCES.get(step_id)
    if sentence is None:
        return text
    assert text.count(sentence) == 1, step_id
    return text.replace(sentence, "")
