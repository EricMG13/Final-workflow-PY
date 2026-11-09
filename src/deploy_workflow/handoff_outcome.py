"""What a module's handoff says it did, as an outcome class; compared with a forecast.

Standard library only: live_check loads this file by path, tools/expectations_backtest imports it.

| Handoff                                                    | Actual class   |
| ---------------------------------------------------------- | -------------- |
| a status word BLOCKED in the module's own or CP-0's handoff | will_refuse    |
| the run stopped at this module (not accepted)              | will_refuse    |
| READY_WITH_LIMITATIONS                                     | limited        |
| READY                                                      | ready          |
| accepted, no recognised status word                        | unconfirmed    |
| no handoff and the run did not stop here (or no record)    | not_reached    |

With no handoff of its own, only CP-0's BLOCKED about the module counts; CP-0's READY or
READY_WITH_LIMITATIONS leaves it not_reached.

`unconfirmed` and `not_reached` are not evidence: against any forecast the verdict is "not testable"
(a live check reports them as findings, never as agreement). A status is the first status word
within 70 characters after the module id, with no other module id between.
"""

import re

STATUS = {"BLOCKED": "will_refuse", "READY_WITH_LIMITATIONS": "limited", "READY": "ready"}
COMPATIBLE = {
    "will_refuse": {"will_refuse"},
    "gap": {"limited", "will_refuse"},
    "limited": {"limited"},
    "ready": {"ready"},
    "check": {"ready", "limited"},
    "information": {"ready", "limited"},
}


def actual_of(
    module: str, own: str | None, cp0: str = "", *, refused: bool = False
) -> tuple[str, str]:
    """The module's class and how it was read. `own` is None when it has no accepted handoff;
    `refused` says the run stopped at this module."""
    pattern = re.compile(
        rf"\b{re.escape(module)}\b(?:(?!CP-)[^\n]){{0,70}}?\b({'|'.join(STATUS)})\b"
    )
    if own is None:
        # Only BLOCKED in CP-0 is evidence for a module with no handoff; READY there is not.
        found = pattern.search(cp0)
        if found and found[1] == "BLOCKED":
            return "will_refuse", "BLOCKED in CP-0 handoff"
        return ("will_refuse", "run stopped here") if refused else ("not_reached", "no handoff")
    for name, text in ((f"{module} handoff", own), ("CP-0 handoff", cp0)):
        if found := pattern.search(text):
            return STATUS[found[1]], f"{found[1]} in {name}"
    return "unconfirmed", "accepted, no status stated"


def verdict(forecast: str, actual: str) -> str:
    if actual in ("unconfirmed", "not_reached"):
        return "not testable"
    return "agreed" if actual in COMPATIBLE[forecast] else "disagreed"
