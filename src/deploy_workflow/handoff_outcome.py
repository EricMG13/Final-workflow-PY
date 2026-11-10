"""What a module's handoff says it did, as an outcome class; compared with a forecast.

Standard library only: live_check loads this file by path, tools/expectations_backtest imports it.

1. The module's own handoff is read first. Its evidence is exact `key: value` lines in the
   handoff's leading `---` front-matter block (prose never counts; values match in any letter
   case, may be single- or double-quoted and may end in ` # comment`; a leading BOM is
   ignored), a line that starts with the label `Module Status:` (case-insensitive; bold,
   backticks, a `> ` quote, a list marker and a final period allowed; a table row never counts;
   a line inside a code fence never counts, nor does a status word there, front matter
   excepted; fences per CommonMark: an
   opening line is indented at most 3 spaces and starts with 3+ backticks or tildes, a backtick
   fence's info string has no backtick, and it closes only on a line of the same character,
   at least as long a run and only whitespace after; unclosed runs to the end), plus a
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

A CP-0 status is the most severe status word in any cell of a table row whose first cell begins
with the module id (a row of another module never counts); in other text it is the first status
word within 70 characters after the module id, with no other module id between. A `Module
Status:` value counts when it begins with a known phrase followed by a period or the line's end
(the rest of the line is ignored).

`unconfirmed` and `not_reached` are not evidence: against any forecast the
verdict is "not testable" (a live check reports them as findings, never as agreement).
"""

import re

STATUS = {"BLOCKED": "will_refuse", "READY_WITH_LIMITATIONS": "limited", "READY": "ready"}
FIELDS = {
    ("qa_status", "blocked"): "will_refuse",
    ("committee_status", "blocked"): "will_refuse",
    ("qa_status", "restricted"): "limited",
    ("committee_status", "restricted"): "limited",
    ("review_status", "provisional"): "limited",
    ("committee_status", "committee ready"): "ready",
}
_WORD_RANK = ["READY", "READY_WITH_LIMITATIONS", "CONDITIONAL", "BLOCKED"]
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
    lines = text.removeprefix("\ufeff").split("\n")
    if lines[0].strip() != "---":
        return []
    pairs: list[tuple[str, str]] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return pairs
        key, sep, value = line.partition(":")
        if sep:
            value = re.sub(r"\s+#.*$", "", value.strip())
            if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            pairs.append((key.strip(), value.strip()))
    return []


MODULE_STATUS = {
    "blocked": "will_refuse",
    "completed with limitations": "limited",
    "completed": "ready",
}


def module_status(line: str) -> str | None:
    """The status value, as written, of a `Module Status:` line, or None. Markup that does not
    change the words is dropped until the text stops changing: runs of *, backticks, a `> `
    blockquote, a list marker, one final period. The label may be in any letter case."""
    previous = None
    while line != previous:
        previous = line
        line = line.strip().replace("*", "").strip("`").removesuffix(".")
        line = re.sub(r"^(?:>|-)[ \t]+", "", line)
    label, sep, value = line.partition(":")
    if not sep or label.strip().lower() != "module status":
        return None
    phrase = re.match(
        r"(completed with limitations|completed|blocked)(?:\.|$)",
        value.strip("` \t"),
        re.IGNORECASE,
    )
    return phrase[1] if phrase else None


def fence_run(line: str) -> tuple[str, int, str]:
    """(character, run length, rest) of a possible fence line (indent <= 3), else ("", 0, "")."""
    stripped = line.lstrip(" ")
    if len(line) - len(stripped) > 3 or stripped[:1] not in ("`", "~"):
        return "", 0, ""
    rest = stripped.lstrip(stripped[0])
    return stripped[0], len(stripped) - len(rest), rest


def unfenced(text: str) -> list[str]:
    """The lines of `text` outside code fences (the fence lines themselves are dropped)."""
    kept: list[str] = []
    fence = ("", 0)  # (character, run length) of the open fence
    for line in text.removeprefix("\ufeff").splitlines():
        char, run, rest = fence_run(line)
        if fence[0]:
            if char == fence[0] and run >= fence[1] and not rest.strip():
                fence = ("", 0)
        elif run >= 3 and not (char == "`" and "`" in rest):
            fence = (char, run)
        else:
            kept.append(line)
    return kept


def status_word(module: str, text: str, words: tuple[str, ...]) -> str | None:
    """The module's status word: in a table row whose first cell begins with the module id, the
    most severe of `words` in any cell; else the first within 70 characters after the id, no
    other module id between (a row of another module is not read)."""
    alt = "|".join(words)
    rows: list[str] = []
    rest: list[str] = []
    for line in text.split("\n"):
        first = line.lstrip().startswith("|") and line.split("|")[1].replace("*", "").strip(" `")
        if first and re.match(r"CP-", first):
            if re.match(rf"{re.escape(module)}\b", first):
                rows += re.findall(rf"\b({alt})\b", line)
        else:
            rest.append(line)
    if rows:
        return max(rows, key=_WORD_RANK.index)
    pattern = rf"\b{re.escape(module)}\b(?:(?!CP-)[^\n]){{0,70}}?\b({alt})\b"
    found = re.search(pattern, "\n".join(rest))
    return found[1] if found else None


def own_status(module: str, own: str) -> tuple[str, str] | None:
    """The most severe (class, how) the module's own handoff states, or None."""
    name = f"{module} handoff"
    found = [
        (FIELDS[(key, value.lower())], f"{key}: {value} in {name}")
        for key, value in front_matter(own)
        if (key, value.lower()) in FIELDS
    ]
    prose = unfenced(own)
    found.extend(
        (MODULE_STATUS[value.lower()], f"Module Status: {value} in {name}")
        for line in prose
        if (value := module_status(line))
    )
    if word := status_word(module, "\n".join(prose), tuple(STATUS)):
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
