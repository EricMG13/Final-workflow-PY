"""What a module's handoff says it did, as an outcome class; compared with a forecast.

Standard library only: live_check loads this file by path, tools/expectations_backtest imports it.

1. The module's own handoff is read first. Its evidence is exact `key: value` lines in the
   handoff's leading `---` front-matter block (prose never counts), a line that starts with the
   label `Module Status:` (bold, backticks, a list marker and a final period
   allowed; case-insensitive; a table row never counts), plus a
   status word after the module id (below). The most severe value wins:
   will_refuse > limited > ready.

| Own handoff value                                              | Actual class |
| -------------------------------------------------------------- | ------------ |
| qa_status or committee_status: Blocked; status word BLOCKED    | will_refuse  |
| qa_status or committee_status: Restricted; review_status:      | limited      |
|   Provisional; status word READY_WITH_LIMITATIONS              |              |
| Module Status: Blocked                                         | will_refuse  |
| Module Status: Completed with Limitations                      | limited      |
| committee_status: Committee Ready; Module Status: Completed;   | ready, only  |
|   status word READY (only when no limited or will_refuse       | then         |
|   value is present)                                            |              |
| committee_status: Draft Only, Requires More Work or            | no result    |
|   Insufficient Information                                     | (go to 2)    |

2. Only when the module states no own status, CP-0's table is read (READY -> ready,
   READY_WITH_LIMITATIONS -> limited, BLOCKED -> will_refuse). CP-0's CONDITIONAL gives
   unconfirmed when the module has its own handoff, will_refuse when it has none.
3. With no handoff of its own and nothing from CP-0 above: will_refuse ("run stopped here") when
   the run stopped at this module (`refused`, even if CP-0 says READY), else not_reached.
4. An accepted handoff with no status anywhere: unconfirmed. CP-0 itself: always unconfirmed.

A CP-0 status is the first status word within 70 characters after the module id, with no other
module id between. `unconfirmed` and `not_reached` are not evidence: against any forecast the
verdict is "not testable" (a live check reports them as findings, never as agreement).
"""

import re

STATUS = {"BLOCKED": "will_refuse", "READY_WITH_LIMITATIONS": "limited", "READY": "ready"}
FIELDS = {
    ("qa_status", "Blocked"): "will_refuse",
    ("committee_status", "Blocked"): "will_refuse",
    ("qa_status", "Restricted"): "limited",
    ("committee_status", "Restricted"): "limited",
    ("review_status", "Provisional"): "limited",
    ("committee_status", "Committee Ready"): "ready",
}
SEVERITY = {"ready": 0, "limited": 1, "will_refuse": 2}
COMPATIBLE = {
    "will_refuse": {"will_refuse"},
    "gap": {"limited", "will_refuse"},
    "limited": {"limited"},
    "ready": {"ready"},
    "check": {"ready", "limited"},
    "information": {"ready", "limited"},
}


def front_matter(text: str) -> list[tuple[str, str]]:
    """The `key: value` lines of the leading `---` block; [] when there is no closed block."""
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return []
    pairs: list[tuple[str, str]] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return pairs
        key, sep, value = line.partition(":")
        if sep:
            pairs.append((key.strip(), value.strip()))
    return []


MODULE_STATUS = {
    "blocked": "will_refuse",
    "completed with limitations": "limited",
    "completed": "ready",
}


def module_status(line: str) -> str | None:
    """The status phrase of a `Module Status:` line, or None. Markup that does not change the
    words is dropped: ** around the label or value, backticks, a list marker, one final period."""
    line = line.strip().replace("**", "").strip("`").strip()
    line = re.sub(r"^[-*][ \t]+", "", line)
    label, sep, value = line.partition(":")
    if not sep or label.strip() != "Module Status":
        return None
    value = value.strip().strip("`").strip().removesuffix(".").strip().lower()
    return value if value in MODULE_STATUS else None


def status_word(module: str, text: str, words: tuple[str, ...]) -> str | None:
    """The first of `words` within 70 characters after the module id, no other module id between."""
    pattern = rf"\b{re.escape(module)}\b(?:(?!CP-)[^\n]){{0,70}}?\b({'|'.join(words)})\b"
    found = re.search(pattern, text)
    return found[1] if found else None


def own_status(module: str, own: str) -> tuple[str, str] | None:
    """The most severe (class, how) the module's own handoff states, or None."""
    name = f"{module} handoff"
    found = [
        (FIELDS[pair], f"{pair[0]}: {pair[1]} in {name}")
        for pair in front_matter(own)
        if pair in FIELDS
    ]
    for line in own.splitlines():
        if not line.lstrip().startswith("|") and (phrase := module_status(line)):
            found.append((MODULE_STATUS[phrase], f"Module Status: {phrase} in {name}"))
    if word := status_word(module, own, tuple(STATUS)):
        found.append((STATUS[word], f"{word} in {name}"))
    # ready only when nothing limited or will_refuse is present: max by severity gives that.
    return max(found, key=lambda f: SEVERITY[f[0]], default=None)


def actual_of(
    module: str, own: str | None, cp0: str = "", *, refused: bool = False
) -> tuple[str, str]:
    """The module's class and how it was read. `own` is None when it has no accepted handoff;
    `refused` says the run stopped at this module."""
    if module == "CP-0":
        return "unconfirmed", "CP-0 is the table, not a module under test"
    if own is not None and (stated := own_status(module, own)):
        return stated
    word = status_word(module, cp0, (*STATUS, "CONDITIONAL"))
    if own is None:
        if word in ("BLOCKED", "CONDITIONAL"):
            return "will_refuse", f"{word} in CP-0 handoff"
        return ("will_refuse", "run stopped here") if refused else ("not_reached", "no handoff")
    if word in STATUS:
        return STATUS[word], f"{word} in CP-0 handoff"
    return "unconfirmed", "accepted, no status stated"


def verdict(forecast: str, actual: str) -> str:
    if actual in ("unconfirmed", "not_reached"):
        return "not testable"
    return "agreed" if actual in COMPATIBLE[forecast] else "disagreed"
