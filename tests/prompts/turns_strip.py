"""Undo the turn budget (CP1H-R4) and the 64-call pack-tools budget (CP1H-R5) in a composed
message: the ``Limits:`` line ends with ``; the step ends after 30 model turns`` and the pack-tools
sentence says ``share 64 calls in one step`` (or ``at most 64 calls in one step``) where it said
32 (the ada415ca budget, which ``invoke_strip`` takes on to 16). Removing the suffix and putting
the 32 back gives the message as it was before both."""

from prompt_support import spec_of

from deploy_vii.live.tools import EXTRACT, READ, SEARCH
from deploy_workflow.prompts.tools import tool_names

# CP1H-R4/R5 budgets pinned as literals: a later constant change must fail this strip.
_MAX_TURNS = 30
_MAX_INVOKES = 64
_BEFORE = 32
_SUFFIX = f"; the step ends after {_MAX_TURNS} model turns"
_SHARE = (f"share {_MAX_INVOKES} calls in one step", f"share {_BEFORE} calls in one step")
_AT_MOST = (f"at most {_MAX_INVOKES} calls in one step", f"at most {_BEFORE} calls in one step")


def undo_turns(step_id: str, text: str) -> str:
    """Drop the turn-budget suffix and put the 32-call wording back (steps with pack tools)."""
    assert text.count(_SUFFIX) == 1, step_id
    offers = any(n in (SEARCH, READ, EXTRACT) for n in tool_names(spec_of(step_id)))
    spans = text.count(_SHARE[0]) + text.count(_AT_MOST[0])
    assert spans == (1 if offers else 0), step_id
    text = text.replace(_SUFFIX, "")
    return text.replace(_SHARE[0], _SHARE[1]).replace(_AT_MOST[0], _AT_MOST[1])
