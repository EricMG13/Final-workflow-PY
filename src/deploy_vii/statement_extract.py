"""Python statement-line extraction from whitespace-aligned page text (task 8.10).

User decision "A" (24 Oct 2026): Python extracts the printed statement lines and the model maps,
corrects and cites them instead of retyping them. One call reads one page's text and reports
only what is printed: each data line's label, its raw numeric cells and their exact `Decimal`
values, the label's indent, the caption above it and the raw header lines above the first data
line. Every extracted row also carries bounded exact `label_candidates` with their physical
line numbers for a separate source-bound label selection, plus a per-cell indicator of whether
the source printed a currency sign. These fields do not change its legacy label, raw values or
flags. It never rounds and never guesses a unit, period, item, statement or sign convention (the
model maps `period_id` and `item_id`). A line the rules cannot parse is never stubbed as
data; a candidate such line (two or more tokens ending in a numeric cell) is recorded in
`ExtractedTable.omitted` as printed, and prose yields an empty table.

Rules (docs/development/live-runner.md, "Statement extraction"):

- A line's cells are separated by two or more spaces, or by a ` | ` pipe (a table row printed
  as `Label | 1,759 | 1,668`: the line is read as if each pipe were two spaces; a row of only
  `-` runs and pipes gives no line, and a line holding a pipe is never a caption or a label
  continuation). A data line is a label (with a letter)
  followed, to the end of the line, by two or more numeric cells: `10,441`, `2.42`, `(1,234)`
  (negative) or a lone em dash, en dash or hyphen (nil: value `None`, raw token kept). A `$`,
  `£` or `€` before a number, alone or attached, is folded into it and not kept in the raw value.
- Leader dots (runs of two or more `.` or `…`, optionally space-separated; a `.` directly before
  a digit is a decimal point and ends a run) between a label and its values are read as two
  spaces, so the label does not hold them and they do not join cells. A currency sign printed
  one space or none after a digit, or after a `)` or `.` that follows a digit, is split from it
  (`(4.99) $ 5.00`); after a word it is not (`$84 and $108` stays label text).
- A single cell of text with no digit and a lowercase letter, not ending in `:`, directly above
  a data line (no blank line between) continues its label; such lines join the label with one
  space and the indent is the first line's. A line ending in `:` is a sub-heading, not joined.
- A line with a letter, no lowercase letter and no digit is a caption; it applies to the data
  lines that follow until the next caption.
- `headers` are the raw lines nearest above the first data line holding two or more four-digit
  years or a month name, with the adjacent such lines above them (blank lines between allowed).
- A line whose numeric cells are all bare four-digit years from 1900 to 2099 with no `$` is a
  header line, not data, only when its label is empty, wholly parenthesised (`(In millions)`),
  or made only of month names, period words (`Year ended December 31`, `Notes`) and unit or scale
  words (`in millions, except per share data`). Any other label makes it a data line, read like any
  other (`Net revenues  2025  1998`), so `headers` never holds a returned data line.
- `omitted` lists, in page order, each candidate line the rules did not return as data: a
  non-blank line of two or more whitespace-separated tokens (after the pipe rewrite) whose
  last token is a numeric cell, or a printed number the cell rules do not read (a leading ASCII
  or Unicode minus `-1,234` `\u221245`, a percent `12.5%`, a decimal comma or dotted thousands
  `1.234,5`; a last lone `)` or `%` is read with the token before it, so `(250 )` and
  `12.5 %` count), and which holds a letter or digit (a row of only nil dashes and pipes is a
  separator), that is neither a returned data line, a returned header line nor a
  header-shaped line ending in a four-digit year (`2025`, `31,2025`: a second table's period
  row). A lone token (a page number) is never a candidate. Such numbers are never read as
  values here.

Flags (task 8.10b, review risks 1-2) inform the model and never drop a line:

- `more_values_than_header_years`: the line has more numeric cells than the table's header
  lines hold four-digit years (counted over all header lines; none counted when the headers
  name no year). A footnote marker `(1)` two spaces before the values reads as a value of -1.
- `label_ends_numeric`: the label's last token is a numeric cell (`1,234`, `$5`, `(12)`, a nil
  dash, a split `(12 )`) or a minus-signed number (`-120`, `\u2212120`), which stops the scan.
  Two numbers one space apart are one text cell, so the scan stops there and they stay
  in the label; a label ending in a year (`Balance, January 1, 2023`) is flagged too.
- `ambiguous_separator`: a value is printed with one dot and exactly three digits after it
  (`1.234`) on a page whose data lines also print a whole number: the dot may be a thousands
  separator (1,234), so the value read (1.234) may be a thousand times too small.
- `footnote_marker`: the header lines hold N > 0 four-digit years and the line has N + 1 raw
  values whose first is `(n)`, or a bare `n` when a header line has a cell that is the word Note or
  Notes on its own, starting left of the leftmost year column (one or two digits, no `$`), and
  ends left of the column where the leftmost four-digit year of the
  header lines starts (both read after the pipe rewrite): that first cell is a footnote marker,
  dropped from `raw_values` and `values` (the label is unchanged), and the line does not also get
  `more_values_than_header_years`. A note reference of several numbers (`7 and 9`,
  `8, 9, 11 and 16`) is label text, two or more spaces after the label; under a Note or Notes
  header it counts as the extra cell: the line has N raw values and the reference ends left of
  that column, and it is dropped from the label (the values are unchanged). Rows below a later
  header line that is not a data row are not under the Note column. Both conditions are
  required: a small first value with no extra value, one right of the first year, or one under no
  Note header (a two-column table under one year) is a value. Under a Note column, a row of N
  values whose first is an unsigned bare number of one or two digits left of the years, with a
  sign folded into a later cell, keeps that number in its label and is flagged
  `label_ends_numeric`. With no year in the headers
  the marker `(n)` still reads as -1 and is flagged as above.

`ExtractedTable.source_id` names the table's source: `extract_pack_statements` sets it and
binds locators per source, so two sources may share a locator; `extract_statement_lines` sets
it only when given one.
"""

import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal

_NUMBER = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_NIL_TOKENS = ("\u2014", "\u2013", "-")  # em dash, en dash, hyphen
_NILS = frozenset(_NIL_TOKENS)
_NIL = "|".join(_NIL_TOKENS)
_SIGNS = frozenset("$\u00a3\u20ac")  # `$`, `£`, `€`
_NUMERIC_CELL = re.compile(
    rf"(?P<dollar>[$\u00a3\u20ac] ?)?(?P<raw>\((?:{_NUMBER})\)|(?:{_NUMBER})|{_NIL})"
)
_CELL = re.compile(r"\S+(?: \S+)*")
# A printed number the cell rules do not read: a leading ASCII or Unicode minus (`-1,234`,
# `\u221245`), a percent (`12.5%`), a decimal comma or dotted thousands (`1.234,5`, `1.234.567`).
_DIGITS = r"[-\u2212]?[$\u00a3\u20ac]?\d(?:[\d,.]*\d)?"
_UNREAD_NUMBER = re.compile(rf"[-\u2212+]?[$\u00a3\u20ac]?(?:\({_DIGITS}\)|{_DIGITS})%?")
_MINUS_NUMBER = re.compile(r"[-\u2212][$\u00a3\u20ac]?\d(?:[\d,.]*\d)?")
# A dot followed by exactly three digits (`1.234`): a decimal point, or a thousands separator
# (a leading group never starts with zero: `0.123` is a decimal).
_DOT_THREE = re.compile(r"\(?[1-9]\d{0,2}\.\d{3}\)?")
_INTEGER = re.compile(r"\(?\d{1,3}(?:,\d{3})*\)?|\(?\d+\)?")
_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_BARE_YEAR = re.compile(r"(?:19|20)\d{2}")
_YEAR_END = re.compile(r"(?<![\d$\u00a3\u20ac])(?:19|20)\d{2}$")
_WORD = re.compile(r"[A-Za-z]+")
_PIPE = re.compile(r"[ \t]*\|[ \t]*")
_MONTH_NAMES = (
    *("January", "February", "March", "April", "May", "June", "July", "August"),
    *("September", "October", "November", "December"),
)
_MONTHS = frozenset((*_MONTH_NAMES, *(name.upper() for name in _MONTH_NAMES)))
_FOOTNOTE = re.compile(r"\(\d{1,2}\)")
_BARE_REF = re.compile(r"\d{1,2}")
_NOTE_HEADER = re.compile(r"Notes?", re.IGNORECASE)
_LEADER = re.compile(r"(?:(?:\.(?!\d)|\u2026) ?){2,}")
_STUCK_SIGN = re.compile(r"(?:(?<=\d)|(?<=\d[).])) ?(?=[$\u00a3\u20ac])")
_NOTE_TAIL = re.compile(r"(?P<head>.*?\S)\s{2,}(?P<ref>\d{1,2}(?:(?:, ?| and |, and )\d{1,2})+)")
_HEADER_WORDS = frozenset(
    (
        *(name.lower() for name in _MONTH_NAMES),
        *("year", "years", "ended", "ending", "fiscal", "month", "months", "week", "weeks"),
        *("quarter", "quarters", "period", "periods", "three", "six", "nine", "twelve"),
        *("for", "the", "as", "of", "at", "and"),
        *("in", "millions", "thousands", "billions", "dollars", "usd", "except", "per"),
        *("share", "data", "par", "value", "amounts", "unaudited", "note", "notes"),
    )
)
_PERIOD_HEADER_WORDS = _HEADER_WORDS | frozenset({"q", "fy", "consolidated", "parent"})
_STATEMENT_TITLE = re.compile(
    r"\b(?:balance sheets?|income statements?|cash flow statements?|statements?\s+of)\b",
    re.IGNORECASE,
)
LineFlag = Literal[
    "more_values_than_header_years", "label_ends_numeric", "footnote_marker", "ambiguous_separator"
]
MORE_VALUES_THAN_HEADER_YEARS: LineFlag = "more_values_than_header_years"
LABEL_ENDS_NUMERIC: LineFlag = "label_ends_numeric"
FOOTNOTE_MARKER: LineFlag = "footnote_marker"
AMBIGUOUS_SEPARATOR: LineFlag = "ambiguous_separator"


@dataclass(frozen=True)
class ExtractedLabelPart:
    """One exact printed label fragment that can be selected for a source row."""

    line_no: int
    text: str


@dataclass(frozen=True)
class ExtractedLine:
    """One printed data line. `line_no` is the 1-based line of the page text holding the values;
    `raw_values[i]` is printed on that line and `values[i]` is its exact Decimal (None for a nil).
    `flags` (module docstring) are computed, in a fixed order; they never drop the line.
    """

    locator: str
    line_no: int
    label: str
    raw_values: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    indent: int
    caption: str | None
    flags: tuple[LineFlag, ...] = ()
    label_candidates: tuple[ExtractedLabelPart, ...] = ()
    currency_values: tuple[bool, ...] = ()


@dataclass(frozen=True)
class OmittedLine:
    """A candidate line (module docstring) not returned as data: `line_no` is 1-based and `text`
    the page line as printed."""

    line_no: int
    text: str


@dataclass(frozen=True)
class ExtractedTable:
    """The data lines of one page's text, in page order, with the raw header lines and the
    candidate lines omitted. `source_id` names the source the page belongs to (None: the text
    was given without one)."""

    locator: str
    headers: tuple[str, ...]
    lines: tuple[ExtractedLine, ...]
    source_id: str | None = None
    omitted: tuple[OmittedLine, ...] = ()
    source_lines: tuple[ExtractedLabelPart, ...] = ()


@dataclass(frozen=True)
class _Cells:
    label: str
    raw_values: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    first_dollar: bool  # a `$` is folded into the first cell
    first_end: int  # the column where the first cell ends, in the line as read
    note_head: str | None = None  # the label before a trailing multi-number note reference
    note_end: int = 0  # the column where that reference ends, in the line as read
    later_sign: bool = False  # a sign is folded into a cell after the first
    currency_values: tuple[bool, ...] = ()


def _value(raw: str) -> Decimal | None:
    if raw in _NILS:
        return None
    if raw.startswith("("):
        # Built from the string, never by negation: `-Decimal` would round to the context.
        return Decimal("-" + raw[1:-1].replace(",", ""))
    return Decimal(raw.replace(",", ""))


_Edit = tuple[int, int, int]  # (start in the new text, new length, old length)


def _rewrite(pattern: re.Pattern[str], replacement: str, text: str) -> tuple[str, list[_Edit]]:
    """`text` with every match of `pattern` replaced, and where each replacement landed."""
    parts: list[str] = []
    edits: list[_Edit] = []
    at = new_at = 0
    for match in pattern.finditer(text):
        parts.append(text[at : match.start()])
        new_at += match.start() - at
        edits.append((new_at, len(replacement), match.end() - match.start()))
        parts.append(replacement)
        new_at += len(replacement)
        at = match.end()
    parts.append(text[at:])
    return "".join(parts), edits


def _before(edits: Sequence[_Edit], column: int) -> int:
    """The column in the text before the edits of a column that is not inside a replacement."""
    shift = 0
    for start, new, old in edits:
        if start + new > column:
            break
        shift += new - old
    return column - shift


def _numeric_tail(text: str) -> bool:
    """Whether `text` holds numeric cells (with their currency signs) and nothing else."""
    cells = [cell.group() for cell in _CELL.finditer(_rewrite(_STUCK_SIGN, "  ", text)[0])]
    return any(c not in _SIGNS for c in cells) and all(
        c in _SIGNS or _NUMERIC_CELL.fullmatch(c) is not None for c in cells
    )


def _strip_leader(line: str) -> tuple[str, list[_Edit]]:
    """`line` with the first leader run that is followed only by numeric cells, and not preceded
    by a numeric cell, read as two spaces: the run between the label and its first value. Dots
    inside a label, or between or after values, stay as printed."""
    match = None
    for match in _LEADER.finditer(line):
        pass
    if match is None:
        return line, []
    before = list(_CELL.finditer(line[: match.start()]))
    if (not before or not _NUMERIC_CELL.fullmatch(before[-1].group())) and _numeric_tail(
        line[match.end() :]
    ):
        text = f"{line[: match.start()]}  {line[match.end() :]}"
        return text, [(match.start(), 2, match.end() - match.start())]
    return line, []


def _cells(line: str) -> _Cells | None:
    """The label and trailing numeric cells of a data line, or None for any other line."""
    if "|" in line:
        line = _PIPE.sub("  ", line)
    line, leaders = _strip_leader(line)
    read, splits = _rewrite(_STUCK_SIGN, "  ", line)
    found: list[tuple[str, bool]] = []  # (raw, a sign is folded in), right to left
    start = len(read)
    first_end = start
    for cell in reversed(list(_CELL.finditer(read))):
        text = cell.group()
        if text in _SIGNS and found and not found[-1][1]:
            found[-1] = (found[-1][0], True)
        elif match := _NUMERIC_CELL.fullmatch(text):
            found.append((match["raw"], match["dollar"] is not None))
            first_end = cell.end()
        else:
            break
        start = cell.start()
    start = _before(splits, start)
    first_end = _before(splits, first_end)
    label = line[:start].strip()
    if len(found) < 2 or not _WORD.search(label):
        return None
    if _is_period_label(label) and all(
        _BARE_YEAR.fullmatch(raw) and not dollar for raw, dollar in found
    ):
        return None
    raws = tuple(raw for raw, _ in reversed(found))
    note = _NOTE_TAIL.fullmatch(label)
    note_head = note["head"] if note and _WORD.search(note["head"]) else None
    return _Cells(
        label=label,
        raw_values=raws,
        values=tuple(_value(raw) for raw in raws),
        first_dollar=found[-1][1],
        first_end=_before(leaders, first_end),
        note_head=note_head,
        note_end=_before(leaders, len(line[:start].rstrip())),
        later_sign=any(dollar for _, dollar in found[:-1]),
        currency_values=tuple(dollar for _, dollar in reversed(found)),
    )


def _is_period_label(label: str) -> bool:
    """A label that makes a line of only bare years a header line (module docstring)."""
    return (
        not label
        or (label.startswith("(") and label.endswith(")"))
        or all(word.lower() in _HEADER_WORDS for word in _WORD.findall(label))
    )


def _is_header(line: str) -> bool:
    return len(_YEAR.findall(line)) >= 2 or bool(_MONTHS.intersection(_WORD.findall(line)))


def _is_caption(stripped: str) -> bool:
    return (
        "|" not in stripped
        and bool(_WORD.search(stripped))
        and not any(c.islower() for c in stripped)
        and not any(c.isdigit() for c in stripped)
    )


def _is_continuation(stripped: str) -> bool:
    return (
        "|" not in stripped
        and _CELL.fullmatch(stripped) is not None
        and any(c.islower() for c in stripped)
        and not any(c.isdigit() for c in stripped)
        and not stripped.endswith(":")
        and not _is_header(stripped)
    )


def _label_candidates(
    lines: Sequence[str],
    row_index: int,
    row_label: str,
    header_indexes: Collection[int],
) -> tuple[ExtractedLabelPart, ...]:
    """Exact contiguous label fragments above and on a row, bounded by blank/header/data lines."""
    first = row_index
    while first > 0:
        previous_index = first - 1
        previous = lines[previous_index]
        stripped = previous.strip()
        if (
            not stripped
            or previous_index in header_indexes
            or _is_period_header(previous)
            or _STATEMENT_TITLE.search(previous)
            or _cells(previous) is not None
        ):
            break
        first -= 1
    parts = tuple(
        ExtractedLabelPart(line_no=index + 1, text=lines[index].strip())
        for index in range(first, row_index)
        if lines[index].strip()
    )
    if not parts and re.fullmatch(r"(?:Basic|Diluted)(?: and diluted)?", row_label, re.IGNORECASE):
        # A colon heading applies to sibling Basic/Diluted rows until the next
        # non-data line. Keep its exact source position rather than losing the
        # family after the first numeric row.
        for index in range(row_index - 1, -1, -1):
            text = lines[index].strip()
            if not text or _cells(lines[index]) is not None:
                continue
            if text.endswith(":") and re.search(r"\bshares?\b", text, re.IGNORECASE):
                parts = (ExtractedLabelPart(line_no=index + 1, text=text),)
            break
    return (*parts, ExtractedLabelPart(line_no=row_index + 1, text=row_label))


def _is_period_header(line: str) -> bool:
    """A year/date line made only of known period, scale and entity-header words."""
    words = _WORD.findall(line)
    return bool(_is_header(line) and all(word.lower() in _PERIOD_HEADER_WORDS for word in words))


def _header_indexes(lines: Sequence[str], first: int) -> tuple[int, ...]:
    """The 0-based indexes of the header block nearest above the 0-based line `first` (the first
    data line), in page order."""
    index = first - 1
    while index >= 0 and not _is_header(lines[index]):
        index -= 1
    block: list[int] = []
    while index >= 0 and (_is_header(lines[index]) or not lines[index].strip()):
        if lines[index].strip():
            block.append(index)
        index -= 1
    return tuple(reversed(block))


def _joined(tokens: list[str]) -> list[str]:
    """`tokens` with a last lone `)` or `%` joined to the token before it: a split parenthesis
    `(250 )` or a spaced percent `12.5 %` printed as one value."""
    if len(tokens) >= 3 and tokens[-1] in {")", "%"}:
        return [*tokens[:-2], tokens[-2] + tokens[-1]]
    return tokens


def _is_omitted_candidate(line: str) -> bool:
    tokens = _joined((_PIPE.sub("  ", line) if "|" in line else line).split())
    if not any(c.isalnum() for c in line):
        return False  # a separator row of nil dashes and pipes
    last = tokens[-1] if len(tokens) >= 2 else ""
    if not (_NUMERIC_CELL.fullmatch(last) or _UNREAD_NUMBER.fullmatch(last)):
        return False
    # A second table's period row (`June 30, 2026 | December 31,2025`) is not a lost value.
    return not (_is_header(line) and _YEAR_END.search(last))


def _label_ends_numeric(label: str) -> bool:
    tokens = _joined(label.split())
    return bool(tokens) and (
        _NUMERIC_CELL.fullmatch(tokens[-1]) is not None
        or _MINUS_NUMBER.fullmatch(tokens[-1]) is not None
    )


def _flags(line: ExtractedLine, years: int, footnote: bool, integers: bool) -> tuple[LineFlag, ...]:
    flags: list[LineFlag] = []
    if years and len(line.raw_values) > years:
        flags.append(MORE_VALUES_THAN_HEADER_YEARS)
    if _label_ends_numeric(line.label):
        flags.append(LABEL_ENDS_NUMERIC)
    if footnote:
        flags.append(FOOTNOTE_MARKER)
    if integers and any(_DOT_THREE.fullmatch(raw) for raw in line.raw_values):
        flags.append(AMBIGUOUS_SEPARATOR)
    return tuple(flags)


def _year_column(headers: Sequence[str]) -> int | None:
    """The column where the leftmost four-digit year of the header lines starts."""
    starts = [
        match.start()
        for header in headers
        if (match := _YEAR.search(_PIPE.sub("  ", header) if "|" in header else header))
    ]
    return min(starts, default=None)


def _footnote_marker(
    line: ExtractedLine, cells: _Cells, years: int, year_column: int | None, note_column: bool
) -> bool:
    """The first cell is a footnote marker `(n)` or, under a "Note" header, a bare note reference:
    left of the first year column, and the one value more than the years that makes it a
    reference."""
    first = line.raw_values[0]
    return (
        years > 0
        and year_column is not None
        and cells.first_end < year_column
        and len(line.raw_values) == years + 1
        and not cells.first_dollar
        and (
            _FOOTNOTE.fullmatch(first) is not None
            or (note_column and _BARE_REF.fullmatch(first) is not None)
        )
    )


def _note_reference(cells: _Cells, years: int, year_column: int | None, note_column: bool) -> bool:
    """The label ends in a several-number note reference (`7 and 9`) under a "Note" header that
    counts as the extra cell: left of the first year column, with exactly the years' values
    after it."""
    return (
        note_column
        and years > 0
        and year_column is not None
        and cells.note_head is not None
        and cells.note_end < year_column
        and len(cells.raw_values) == years
    )


def extract_statement_lines(
    text: str, locator: str, source_id: str | None = None
) -> ExtractedTable:
    """The printed data lines of one page's text (module docstring rules); prose yields none."""
    lines = [line.removesuffix("\r") for line in text.split("\n")]
    found: list[ExtractedLine] = []
    read: list[_Cells] = []
    first: int | None = None
    caption: str | None = None
    pending: list[str] = []  # continuation lines directly above the current line
    for index, line in enumerate(lines):
        stripped = line.strip()
        cells = _cells(line)
        if cells is not None:
            first = index if first is None else first
            head = pending[0] if pending else line
            found.append(
                ExtractedLine(
                    locator=locator,
                    line_no=index + 1,
                    label=" ".join((*(part.strip() for part in pending), cells.label)),
                    raw_values=cells.raw_values,
                    values=cells.values,
                    indent=len(head) - len(head.lstrip()),
                    caption=caption,
                    currency_values=cells.currency_values,
                )
            )
            read.append(cells)
            pending = []
        elif _is_caption(stripped):
            caption = stripped
            pending = []
        elif _is_continuation(stripped):
            pending.append(line)
        else:
            pending = []
    header_at = () if first is None else _header_indexes(lines, first)
    headers = tuple(lines[index] for index in header_at)
    header_boundaries = set(header_at)
    header_boundaries.update(
        index for index, raw_line in enumerate(lines) if _is_period_header(raw_line)
    )
    years = sum(len(_YEAR.findall(header)) for header in headers)
    # Any value printed as a whole number makes a `1.234` beside it ambiguous.
    integers = any(_INTEGER.fullmatch(raw) for line in found for raw in line.raw_values)
    flagged: list[ExtractedLine] = []
    year_column = _year_column(headers)
    note_header = year_column is not None and any(
        _NOTE_HEADER.fullmatch(cell.group()) and cell.start() < year_column
        for header in headers
        for cell in _CELL.finditer(_PIPE.sub("  ", header) if "|" in header else header)
    )
    data_at = {line.line_no - 1 for line in found}
    note_until = next(
        (
            index
            for index in range(first or 0, len(lines))
            if index not in data_at and _is_header(lines[index])
        ),
        len(lines),
    )
    for printed, parsed in zip(found, read, strict=True):
        note_column = note_header and printed.line_no - 1 < note_until
        footnote = _footnote_marker(printed, parsed, years, year_column, note_column)
        data = (
            replace(
                printed,
                raw_values=printed.raw_values[1:],
                values=printed.values[1:],
                currency_values=printed.currency_values[1:],
            )
            if footnote
            else printed
        )
        if not footnote and parsed.note_head is not None:
            footnote = _note_reference(parsed, years, year_column, note_column)
            if footnote:
                head = printed.label.removesuffix(parsed.label).rstrip()
                data = replace(data, label=" ".join(filter(None, (head, parsed.note_head))))
        if (
            not footnote
            and note_column
            and parsed.later_sign
            and not parsed.first_dollar
            and year_column is not None
            and parsed.first_end < year_column
            and len(printed.raw_values) == years
            and _BARE_REF.fullmatch(printed.raw_values[0]) is not None
        ):
            data = replace(
                printed,
                label=f"{printed.label} {printed.raw_values[0]}",
                raw_values=printed.raw_values[1:],
                values=printed.values[1:],
                currency_values=printed.currency_values[1:],
            )
        flagged.append(replace(data, flags=_flags(data, years, footnote, integers)))
    bounded: list[ExtractedLine] = []
    for flagged_line in flagged:
        row_cells = _cells(lines[flagged_line.line_no - 1])
        assert row_cells is not None
        bounded.append(
            replace(
                flagged_line,
                label_candidates=_label_candidates(
                    lines, flagged_line.line_no - 1, row_cells.label, header_boundaries
                ),
            )
        )
    kept = {line.line_no - 1 for line in found}.union(header_at)
    omitted = tuple(
        OmittedLine(line_no=index + 1, text=text)
        for index, text in enumerate(lines)
        if index not in kept and _is_omitted_candidate(text)
    )
    return ExtractedTable(
        locator=locator,
        headers=headers,
        lines=tuple(bounded),
        source_id=source_id,
        omitted=omitted,
        source_lines=tuple(
            ExtractedLabelPart(line_no=index + 1, text=line.strip())
            for index, line in enumerate(lines)
            if line.strip()
        ),
    )


def _objects(value: object, missing: str, not_object: str) -> list[Mapping[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(missing)
    objects: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(not_object)
        objects.append(item)
    return objects


def _pack_spans(pack_json: Mapping[str, object]) -> tuple[list[str], list[tuple[str, str, str]]]:
    """The source ids, and (source_id, locator, text) of every span, in pack order; a malformed
    pack raises."""
    ids: list[str] = []
    found: list[tuple[str, str, str]] = []
    sources = pack_json.get("sources")
    for source in _objects(sources, "pack has no sources list", "a source is not an object"):
        source_id = source.get("source_id")
        if not isinstance(source_id, str):
            raise ValueError("a source has no string source_id")
        ids.append(source_id)
        of = f"of source {source_id!r}"
        spans = source.get("spans")
        for span in _objects(
            spans, f"source {source_id!r} has no spans list", f"a span {of} is not an object"
        ):
            locator, text = span.get("locator"), span.get("text")
            if not isinstance(locator, str):
                raise ValueError(f"a span {of} has no string locator")
            if not isinstance(text, str):
                raise ValueError(f"span {locator!r} {of} has no string text")
            found.append((source_id, locator, text))
    return ids, found


def extract_pack_statements(
    pack_json: Mapping[str, object],
    locators: Iterable[str] | None = None,
    source_id: str | None = None,
) -> tuple[ExtractedTable, ...]:
    """One table per span of `sources[*].spans`, in pack order; read-only, no file I/O.

    With `source_id` given, only that source's spans (an id the pack lacks raises); with
    `locators` given, only those spans. Each table carries its `source_id`, so a locator two
    sources share yields one table per source (task 8.10b); a locator twice in one source in
    scope raises, as its table would be ambiguous. A requested locator that no span in scope
    has raises too. Every span in scope yields a table, an empty one for a page without data
    lines.
    """
    if isinstance(locators, str):
        # A str is an Iterable[str] of characters; reading it so would miss every page.
        raise TypeError("locators must be an iterable of locators, not one string")
    wanted = None if locators is None else frozenset(locators)
    ids, spans = _pack_spans(pack_json)
    if source_id is not None and source_id not in ids:
        raise ValueError(f"source {source_id!r} is not in the pack")
    bound: set[tuple[str, str]] = set()
    tables: list[ExtractedTable] = []
    for owner, locator, text in spans:
        if (source_id is not None and owner != source_id) or (
            wanted is not None and locator not in wanted
        ):
            continue
        if (owner, locator) in bound:
            raise ValueError(
                f"locator {locator!r} is twice in source {owner!r}; an extracted table names "
                "its span by source and locator"
            )
        bound.add((owner, locator))
        tables.append(extract_statement_lines(text, locator, source_id=owner))
    if wanted is not None and (missing := sorted(wanted - {loc for _, loc in bound})):
        where = "the pack" if source_id is None else f"source {source_id!r}"
        raise ValueError(f"locators not in {where}: {missing}")
    return tuple(tables)
