"""Undo the S13 run-text sentences in a composed message: ``FIGURE_WORDS_RULE`` (S13 A04/C07,
appended to the source_readiness run-text rule and the narrative/readiness prose rule) and
``FIGURE_PERIOD_RULE`` (S13 A05, appended to every rule that admits a ``{ref|unit}`` figure).
Removing exactly those sentences and the space before each gives the message the frozen digests
pinned before the fix. Each sentence is asserted to occur once in the steps that carry it and
nowhere else, so the strip cannot hide the sentence in a step that should not have it."""

from deploy_vii.live.prompts import FIGURE_PERIOD_RULE, FIGURE_WORDS_RULE

WORDS_STEPS = frozenset({"narrative", "readiness", "source_readiness"})
PERIOD_STEPS = frozenset(
    {
        "business_context",
        "committee_challenge",
        "credit_synthesis",
        "downside_pathway",
        "earnings_quality",
        "forward_credit_model",
        "legal_covenants",
        "peer_benchmark",
        "rating_triggers",
        "relative_value",
        "restructuring_fulcrum",
    }
)
S13_SENTENCES = (
    (" " + FIGURE_WORDS_RULE, WORDS_STEPS),
    (" " + FIGURE_PERIOD_RULE, PERIOD_STEPS),
)


def undo_s13(step_id: str, text: str) -> str:
    """Remove the S13 sentences from a composed message of step ``step_id``."""
    for sentence, steps in S13_SENTENCES:
        assert text.count(sentence) == (step_id in steps), (step_id, sentence)
        text = text.replace(sentence, "")
    return text
