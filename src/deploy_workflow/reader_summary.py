"""Check a handoff's reader section: plain language that restates only what the handoff already says."""

import re
from typing import NamedTuple

BOTTOM_LINE_WORDS, LIMITATION_WORDS, FINDING_WORDS, MAX_FINDINGS = 40, 30, 30, 5
CONFIDENCE = ("High", "Medium", "Low", "Not assessable")
HEADING = re.compile(r"^### Reader summary[ \t]*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^#{2,3} ", re.MULTILINE)
FIRST_UNDER_FINDINGS = re.compile(r"^## Findings[ \t]*\n\s*\Z", re.MULTILINE)
TABLES = (
    ("Bottom line", "Confidence", "Main limitation"),
    ("Finding", "Creditor impact", "Confidence"),
)
CODE = re.compile(r"\bCP-[A-Z0-9]+\b|\bT\d+[A-Z]?\.\d+\b|\b[0-9A-Fa-f]{16,}\b")
# A number as the reader sees it: the longest run of digits at that place (3.14 is read whole,
# never as 3.1; a malformed 1.2.3 or 12,5 is still read, as 1.2 and 3, or 12 and 5), with the
# sign it was written with (a leading minus, or parentheses) and the unit or scale beside it.
_UNIT = (
    r"%|x\b|pp\b|bps\b|\s?per ?cent\b"
    r"|(?:\s?(?:US\$|USD|\$|EUR|€|GBP|£))?\s?(?:thousands?|millions?|billions?|trillions?|bn|mm|k|m)\b"
)
NUMBER = re.compile(
    r"(?<!\d)(?P<open>\()?(?P<minus>(?<![\w)])[-\u2212])?"
    r"(?P<n>\d+(?:,\d{3}(?!\d))*(?:\.\d+)?)"
    rf"(?P<u1>{_UNIT})?(?P<close>\))?(?P<u2>{_UNIT})?",
    re.IGNORECASE,
)
SCALES = {
    "thousand": "k",
    "thousands": "k",
    "k": "k",
    "million": "m",
    "millions": "m",
    "mm": "m",
    "m": "m",
    "billion": "b",
    "billions": "b",
    "bn": "b",
    "trillion": "t",
    "trillions": "t",
}


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip()[1:-1])]


def _tables(section: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    in_table = False
    for line in section.splitlines():
        is_row = line.lstrip().startswith("|") and line.rstrip().endswith("|")
        if is_row and not in_table:
            tables.append([])
        if is_row and not set(line) <= set("|-: \t"):
            tables[-1].append(_cells(line))
        in_table = is_row
    return tables


def _cell_issues(name: str, value: str, limit: int) -> tuple[str, ...]:
    if not value:
        return (f"Reader summary {name} is empty",)
    count = len(value.split())
    return (
        (f"Reader summary {name} has {count} words; the limit is {limit}",) if count > limit else ()
    )


def _row_issues(
    rows: list[list[str]], columns: tuple[str, ...], limits: tuple[tuple[str, int], ...]
) -> tuple[str, ...]:
    issues: list[str] = []
    place = {name: at for at, name in enumerate(columns)}
    for row in rows:
        if len(row) != len(columns):
            issues.append(f"Reader summary row must have three cells: {' | '.join(row)}")
            continue
        for name, limit in limits:
            issues += _cell_issues(name.lower(), row[place[name]], limit)
        if row[place["Confidence"]] not in CONFIDENCE:
            issues.append(
                f"Reader summary confidence {row[place['Confidence']]!r} is not one of {', '.join(CONFIDENCE)}"
            )
    return tuple(issues)


def _table_issues(tables: list[list[list[str]]]) -> tuple[str, ...]:
    if len(tables) != len(TABLES):
        return (
            f"Reader summary needs two tables, found {len(tables)}: headed {' / '.join(TABLES[0])} and {' / '.join(TABLES[1])}",
        )
    for rows, columns in zip(tables, TABLES, strict=True):
        if not rows or tuple(rows[0]) != columns:
            return (f"Reader summary table must be headed {' | '.join(columns)}",)
    calls, findings = tables[0][1:], tables[1][1:]
    if len(calls) != 1:
        return (f"Reader summary needs one row in its first table, found {len(calls)}",)
    if not 1 <= len(findings) <= MAX_FINDINGS:
        return (f"Reader summary needs 1 to {MAX_FINDINGS} findings, found {len(findings)}",)
    return _row_issues(
        calls,
        TABLES[0],
        (("Bottom line", BOTTOM_LINE_WORDS), ("Main limitation", LIMITATION_WORDS)),
    ) + _row_issues(
        findings, TABLES[1], (("Finding", FINDING_WORDS), ("Creditor impact", FINDING_WORDS))
    )


class _Figure(NamedTuple):
    number: str
    negative: bool
    unit: str | None
    shown: str


def _unit(written: str | None) -> str | None:
    """The unit or scale of a figure, spelled one way: `%`, `x`, `k`, `m`, `b`, ..."""
    if not written:
        return None
    word = re.sub(r"^(?:us\$|usd|\$|eur|€|gbp|£)?\s*", "", written.strip().casefold())
    return "%" if "cent" in word else SCALES.get(word, word)


def _figures(text: str) -> list[_Figure]:
    return [
        _Figure(
            found["n"],
            bool(found["minus"] or (found["open"] and found["close"])),
            _unit(found["u1"] or found["u2"]),
            found[0].strip(),
        )
        for found in NUMBER.finditer(CODE.sub(" ", text))
    ]


def _unmatched_numbers(section: str, rest: str) -> tuple[str, ...]:
    """Each summary figure must appear in the handoff with its sign and, where both state one,
    its unit or scale: 12.3% is not (12.3)%, 4.1x is not 4.1%, 250 thousand is not 250 million.

    A number matches only as a whole number: 3.1 is not in 3.14, and 3.14 is not in 13.14.
    """
    held = _figures(rest)
    issues: dict[str, str] = {}
    for figure in dict.fromkeys(_figures(section)):
        same = [h for h in held if h.number == figure.number]
        if not same:
            issues.setdefault(
                figure.number,
                f"Reader summary number {figure.number} does not appear in the handoff",
            )
        elif not any(
            h.negative == figure.negative
            and (h.unit == figure.unit or None in (h.unit, figure.unit))
            for h in same
        ):
            written = ", ".join(dict.fromkeys(h.shown for h in same[:3]))
            issues.setdefault(
                figure.shown,
                f"Reader summary number {figure.shown} does not match the handoff, which writes "
                f"it as {written}: keep the sign and unit as written",
            )
    return tuple(issues.values())


def reader_issues(text: str) -> tuple[str, ...]:
    """Every problem with the handoff's reader section; empty when it is valid."""
    text = text.replace("\r\n", "\n")
    headings = list(HEADING.finditer(text))
    if not headings:
        return ("Reader summary section is missing",)
    if len(headings) > 1:
        return ("Reader summary appears more than once",)
    start = headings[0].end()
    following = NEXT_HEADING.search(text, start)
    end = following.start() if following else len(text)
    section, rest = text[start:end], text[: headings[0].start()] + text[end:]
    if not FIRST_UNDER_FINDINGS.search(text, 0, headings[0].start()):
        return ("Reader summary must come first under ## Findings",)
    codes = tuple(
        f"Reader summary must not name internal reference {code}"
        for code in dict.fromkeys(CODE.findall(section))
    )
    return codes + _table_issues(_tables(section)) + _unmatched_numbers(section, rest)
