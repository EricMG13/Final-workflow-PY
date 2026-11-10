"""What a module's handoff says it did, as an outcome class; compared with a forecast.

Standard library only: live_check loads this file by path, tools/expectations_backtest imports it.

1. The module's own handoff is read first. Its evidence is exact `key: value` lines in the
   handoff's leading `---` front-matter block (prose never counts; values match in any letter
   case, may be single- or double-quoted and may end in ` # comment`; a leading BOM is
   ignored), a line that starts with the label `Module Status:` (case-insensitive; bold,
   backticks, a `> ` quote, a list marker and a final period allowed, text may follow a
   backticked value; a table row never counts; a line inside a code fence never counts, nor
   does a status word there; front matter is not scanned for fences; lines end at \\n or
   \\r\\n only; fences per CommonMark: an
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

2. Only when the module states no own status, CP-0 is read: its table row and its prose
   status for the module both count, each status word mapped to a class for this module
   (READY -> ready, READY_WITH_LIMITATIONS -> limited, BLOCKED -> will_refuse; CONDITIONAL
   gives nothing when the module has its own handoff, will_refuse when it has none), and the
   worst class wins; a word that gives no class contributes nothing.
3. With no handoff of its own, CP-0 gives only will_refuse (BLOCKED or CONDITIONAL); READY
   and READY_WITH_LIMITATIONS give nothing. With nothing from CP-0 above: will_refuse ("run
   stopped here") when the run stopped at this module (`refused`, even if CP-0 says READY),
   else not_reached.
4. An accepted handoff with no status anywhere: unconfirmed. CP-0 itself: always unconfirmed.

A CP-0 status is the most severe status word in any cell of a table row whose first cell is the
module id alone or the id plus a label (id, optional whitespace, then a colon or a dash after
whitespace; case-insensitive; `*`, backticks and a leading list marker `- ` or `N. ` are
dropped from the cell first; so `CP-4.1`, `CP-4a`, `CP-4-1` and `CP-4 (draft)` are not CP-4's;
a row of another module never counts, nor is it read as text); in other text it is the first status
word within 70 characters after the module id (not followed by `.digit`, `-digit` or a letter),
with no other module id between, and, in CP-0 prose only, a status word (any letter case)
followed by `:` and a list of module ids that includes it (`Blocked: CP-1, CP-4 and CP-5`; same
id boundary; the word starts the line after list/markup characters only, is not negated, and the
ids stop at the first word that is not an id or a separator). A `Module
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
    change the words is dropped in one linear pass: *, leading backticks, `> ` blockquotes and
    list markers, trailing periods, backticks and whitespace. The label may be in any case."""
    line = re.sub(r"^(?:[`\s]|[>-](?=[ \t]))+", "", line.replace("*", ""))
    line = re.sub(r"(?<![\s`.])[\s`.]+$", "", line)
    label, sep, value = line.partition(":")
    if not sep or label.strip().lower() != "module status":
        return None
    phrase = re.match(
        r"(completed with limitations|completed|blocked)`*(?:\.|$)",
        value.lstrip("` \t"),
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
    """The lines of `text` outside code fences (the fence lines themselves are dropped). Lines end
    at \\n or \\r\\n only; the leading front matter is kept whole and not scanned for fences."""
    lines = re.split(r"\r?\n", text.removeprefix("\ufeff"))
    closing = next((i for i, x in enumerate(lines[1:], 1) if x.strip() == "---"), 0)
    head = closing + 1 if lines[0].strip() == "---" else 0
    kept = lines[:head]
    fence = ("", 0)  # (character, run length) of the open fence
    for line in lines[head:]:
        char, run, rest = fence_run(line)
        if fence[0]:
            if char == fence[0] and run >= fence[1] and not rest.strip():
                fence = ("", 0)
        elif run >= 3 and not (char == "`" and "`" in rest):
            fence = (char, run)
        else:
            kept.append(line)
    return kept


def status_words(module: str, text: str, words: tuple[str, ...], both: bool = False) -> list[str]:
    """The module's status words: those in any cell of a table row whose first cell is the module id
    alone or id plus a label (markup and list marker dropped); else the first within 70 characters
    after the id, no other module id between (another module's row is not read), and any word
    followed by `:` and a list of ids that includes the module (`Blocked: CP-1, CP-4`; any letter
    case, and only with `both`, i.e. CP-0 text). That form counts only when the status word starts
    the line after list/markup characters (`-*+>_`, backticks, `N.`), so `Not blocked:` and
    `Unblocked:` never count; the ids are read up to the first word that is not an id or a
    separator (`,` `&` `/` `and`), so `Blocked: CP-4 because CP-1 ...` lists only CP-4.
    With `both` the row words and the prose words are all returned."""
    alt = "|".join(words)
    rows: list[str] = []
    rest: list[str] = []
    for line in text.split("\n"):
        first = line.lstrip().startswith("|") and re.sub(
            r"^(?:-|\d+\.)\s+", "", re.sub(r"[*`]", "", line.split("|")[1]).strip()
        )
        if first and re.match(r"CP-", first, re.IGNORECASE):
            if re.fullmatch(rf"{re.escape(module)}(?:\s*:.*|\s+[-–—].*)?", first, re.IGNORECASE):
                rows += re.findall(rf"\b({alt})\b", line)
        else:
            rest.append(line)
    if rows and not both:
        return rows
    prose = "\n".join(rest)
    ident = r"CP-\w+(?!\w|\.\d|-\d)"
    found = re.search(
        rf"\b{re.escape(module)}\b(?!\.\d|-\d)(?:(?!CP-)[^\n]){{0,70}}?\b({alt})\b", prose
    )
    sep = r"(?:[ \t]*[,&/][ \t]*|[ \t]+)(?:and[ \t]+)?"
    lead = r"(?m)^(?:[ \t>*+_`-]|\d+\.)*"
    listed = rf"{lead}({alt})[*_`]*[ \t]*:[ \t*_`]*((?:{ident}{sep})*{ident})"
    rows += [found[1]] if found else []
    if both:  # the status-colon-id form is read in CP-0 prose only, never in a module's own handoff
        rows += [
            m[1].upper()
            for m in re.finditer(listed, prose, re.IGNORECASE)
            if module.upper() in (i.upper() for i in re.findall(ident, m[2]))
        ]
    return rows


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
    found.extend(
        (STATUS[word], f"{word} in {name}")
        for word in status_words(module, "\n".join(prose), tuple(STATUS))
    )
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
    # CP-0 rows and prose are both read; the worst class wins. With no own handoff only BLOCKED and
    # CONDITIONAL count (rule 3); with one, CONDITIONAL gives nothing.
    read = [
        (STATUS.get(word, "will_refuse"), word)
        for word in status_words(module, cp0, (*STATUS, "CONDITIONAL"), both=True)
        if (own is None and word in ("BLOCKED", "CONDITIONAL"))
        or (own is not None and word != "CONDITIONAL")
    ]
    if read:
        cls, word = max(read, key=lambda r: SEVERITY[r[0]])
        return cls, f"{word} in CP-0 handoff"
    if own is None:
        return ("will_refuse", "run stopped here") if refused else ("not_reached", "no handoff")
    return "unconfirmed", "accepted, no status stated"


def verdict(forecast: str, actual: str) -> str:
    if actual in ("unconfirmed", "not_reached"):
        return "not testable"
    return "agreed" if actual in COMPATIBLE[forecast] else "disagreed"
