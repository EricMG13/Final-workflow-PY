"""Undo the rule-5 finish text (CP1H-R3) in a composed message: the closing instruction says that
a ``valid`` answer, or an ``invalid`` one that does not reopen the step, ends it, and what to do
when an ``invalid`` answer reopens the step. Swapping the new sentences back for the old ones
gives the message as it was before: ``valid`` or ``invalid`` ended the step, and an invalid step
was repaired in a later attempt with a REPAIR block."""

_NEW = (
    " If it answers `invalid` and its result says the step is reopened, correct the object as the"
    " result directs and call it again. Once it answers `valid`, or `invalid` without reopening"
    " the step, the step is over."
)
_OLD = (
    " Once it answers `valid` or `invalid` the step is over, and an invalid step is repaired in a"
    " later attempt with a REPAIR block."
)


def undo_finish(step_id: str, text: str) -> str:
    """Put the old finish sentences back (every step carries the finish text exactly once)."""
    assert text.count(_NEW) == 1, step_id
    return text.replace(_NEW, _OLD)
