"""The period CP-1 states on a quarter column's trailing ratio (S13 C01).

A twelve-month ratio (leverage, coverage, debt ratios) in a quarter column is calculated from the
four quarters ending at that quarter, so CP-1 T4.10 states `LTM <quarter label>: <start> to <end>`
for it: `end` is the quarter's end, `start` is the first day of the window, or `null` while the
window is incomplete (no earlier quarters). Consumers that select a quarter column's fact by its
dates accept that statement through this one function.
"""

import re
from datetime import date

from deploy_vii.model.periods import LTM_DAYS

_STATED = re.compile(
    r"LTM (?P<label>[^:]+): (?P<start>null|\d{4}-\d{2}-\d{2}) to (?P<end>\d{4}-\d{2}-\d{2})"
)


def states_trailing_period(stated: str | None, end: str, label: str | None = None) -> bool:
    """Whether `stated` is the trailing period ending `end` (an ISO date), of the quarter column
    `label` when given: a `null` start, or a start that opens a 364 to 371 day window."""
    found = _STATED.fullmatch(stated or "")
    if found is None or found["end"] != end or (label is not None and found["label"] != label):
        return False
    if found["start"] == "null":
        return True
    try:
        days = (date.fromisoformat(end) - date.fromisoformat(found["start"])).days + 1
    except ValueError:
        return False
    return LTM_DAYS[0] <= days <= LTM_DAYS[1]
