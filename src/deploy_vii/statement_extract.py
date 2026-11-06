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

Rules (this docstring is their only statement):

- A line's cells are separated by two or more spaces, or by a ` | ` pipe (a table row printed
  as `Label | 1,759 | 1,668`: the line is read as if each pipe were two spaces; a row of only
  `-` runs and pipes gives no line, and a line holding a pipe is never a caption or a label
  continuation). A data line is a label (with a letter)
  followed, to the end of the line, by two or more numeric cells: `10,441`, `2.42`, `(1,234)`,
  `(1,234 )` or `($120)` (negative), `-45`, `−45` or `–45` (a minus before the number),
  `1,234-` (a trailing minus) or a lone em dash, en dash or hyphen (nil: value `None`, raw token
  kept). A `$`, `£` or `€` before a number, alone or attached (also inside its parentheses), is
  folded into it and not kept in the raw value; a lone `€` printed one space or none after a
  number, or any lone sign ending the line after one, is that number's suffix.
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
  A later period row (a header line of only period, scale and entity words holding two or more
  years) between two data lines starts a new table: the lines below it are flagged against its
  own header block, while `headers` stays the first table's.
- A line whose numeric cells are all bare four-digit years from 1900 to 2099 with no `$` is a
  header line, not data, only when its label is empty, wholly parenthesised (`(In millions)`),
  or made only of month names, period words (`Year ended December 31`, `Notes`) and unit or scale
  words (`in millions, except per share data`). Any other label makes it a data line, read like any
  other (`Net revenues  2025  1998`), so `headers` never holds a returned data line.
- `omitted` lists, in page order, each candidate line the rules did not return as data: a
  non-blank line of two or more whitespace-separated tokens (after the pipe rewrite) whose
  last token is a numeric cell and which holds a letter or digit (a row of only nil dashes and
  pipes is a separator), that is neither a returned data line, a returned header line
  nor a header-shaped line ending in a bare four-digit year (a second table's period row); or
  a labelled line that is not a header whose last cell holds a digit and no letter (`21.5%`). A
  lone token (a page number) is never a candidate.

Flags (task 8.10b, review risks 1-2) inform the model and never drop a line:

- `more_values_than_header_years`: the line has more numeric cells than its table's year line
  holds four-digit years. The year line is the header line nearest the data holding two or more
  years, else the nearest holding one (a dated title such as `December 31, 2025 and 2024` above
  the column row does not add its years); none counted when the headers name no year. A footnote
  marker `(1)` two spaces before the values reads as a value of -1.
- `label_ends_numeric`: the label's last token is a numeric cell (`1,234`, `$5`, `(12)`, a nil
  dash). Two numbers one space apart are one text cell, so the scan stops there and they stay
  in the label; a label ending in a year (`Balance, January 1, 2023`) is flagged too.
- `footnote_marker`: the header lines hold N > 0 four-digit years and the line has N + 1 raw
  values whose first is `(n)`, or a bare `n` when a header line has a cell that is the word Note or
  Notes on its own, starting left of the leftmost year column (one or two digits, no `$`), and
  ends left of the column where the year line's first four-digit year starts (both read after
  the pipe rewrite): that first cell is a footnote marker, dropped from `raw_values` and
  `values` (the label is unchanged), and the line does not also get
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
_EURO = "\u20ac"
_MINUS = "-\u2212\u2013"  # hyphen-minus, minus sign, en dash: a minus printed before a number
_NUMERIC_CELL = re.compile(
    rf"(?P<dollar>[$\u00a3\u20ac] ?)?(?P<raw>\( ?(?P<inner>[$\u00a3\u20ac] ?)?(?:{_NUMBER}) ?\)"
    rf"|[{_MINUS}](?:{_NUMBER})|(?:{_NUMBER})-?|{_NIL})"
)
_CELL = re.compile(r"\S+(?: \S+)*")
_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_BARE_YEAR = re.compile(r"(?:19|20)\d{2}")
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
LineFlag = Literal["more_values_than_header_years", "label_ends_numeric", "footnote_marker"]
MORE_VALUES_THAN_HEADER_YEARS: LineFlag = "more_values_than_header_years"
LABEL_ENDS_NUMERIC: LineFlag = "label_ends_numeric"
FOOTNOTE_MARKER: LineFlag = "footnote_marker"


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
    digits = raw.strip(f"() {_MINUS}").replace(",", "")
    # Built from the string, never by negation: `-Decimal` would round to the context.
    negative = raw[0] in f"({_MINUS}" or raw.endswith("-")
    return Decimal(("-" if negative else "") + digits)


def _raw(match: re.Match[str]) -> str:
    """The printed numeric cell without its currency signs (`($120)` reads `(120)`)."""
    if match["inner"] is None:
        return match["raw"]
    at = match.start("raw")
    return match["raw"][: match.start("inner") - at] + match["raw"][match.end("inner") - at :]


def _unpipe(line: str) -> str:
    """`line` read as if each ` | ` pipe were two spaces."""
    return _PIPE.sub("  ", line) if "|" in line else line


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


def _scan(read: str, suffix_at: Collection[int]) -> tuple[list[tuple[str, bool]], int, int]:
    """The trailing numeric cells of `read` as (raw, a sign is folded in), right to left, with
    the column where the first of them starts and where it ends. A lone sign attaches to the
    number on its right, except a `€` split from the number on its left (`suffix_at` holds the
    columns where such split signs start) or a lone sign ending the line: those are the left
    number's suffix."""
    found: list[tuple[str, bool]] = []
    start = first_end = len(read)
    suffix = False  # the cell to the left carries the sign just scanned
    for cell in reversed(list(_CELL.finditer(read))):
        text = cell.group()
        match = _NUMERIC_CELL.fullmatch(text)
        if (
            text in _SIGNS
            and not suffix
            and cell.start() in suffix_at
            and (text == _EURO or not found)
        ):
            suffix = True
        elif text in _SIGNS and found and not found[-1][1] and not suffix:
            found[-1] = (found[-1][0], True)
        elif match is not None:
            folded = match["dollar"] is not None or match["inner"] is not None
            found.append((_raw(match), folded or suffix))
            suffix = False
            first_end = cell.end()
        else:
            break
        start = cell.start()
    if suffix and found:  # no number to the left after all: the sign prefixes its right cell
        found[-1] = (found[-1][0], True)
    return found, start, first_end


def _cells(line: str) -> _Cells | None:
    """The label and trailing numeric cells of a data line, or None for any other line."""
    line, leaders = _strip_leader(_unpipe(line))
    read, splits = _rewrite(_STUCK_SIGN, "  ", line)
    found, start, first_end = _scan(read, {at + new for at, new, _ in splits})
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


def _header_indexes(
    lines: Sequence[str], first: int, data_at: Collection[int] = ()
) -> tuple[int, ...]:
    """The 0-based indexes of the header block nearest above the 0-based line `first` (a table's
    first data line), in page order; a data line (`data_at`) is never in it and ends the search."""
    index = first - 1
    while index >= 0 and index not in data_at and not _is_header(lines[index]):
        index -= 1
    block: list[int] = []
    while (
        index >= 0
        and index not in data_at
        and (_is_header(lines[index]) or not lines[index].strip())
    ):
        if lines[index].strip():
            block.append(index)
        index -= 1
    return tuple(reversed(block))


def _is_period_row(line: str) -> bool:
    """A later table's period row: a period header line holding two or more four-digit years."""
    return len(_YEAR.findall(line)) >= 2 and _is_period_header(line)


def _is_omitted_candidate(line: str) -> bool:
    read = _unpipe(line)
    tokens = read.split()
    if not any(c.isalnum() for c in line):
        return False  # a separator row of nil dashes and pipes
    if len(tokens) < 2:
        return False
    # A second table's period row (`June 30, 2026 | December 31, 2025`) is not a lost value.
    if _is_header(line) and _BARE_YEAR.fullmatch(tokens[-1]):
        return False
    if _NUMERIC_CELL.fullmatch(tokens[-1]):
        return True
    # A row of figures the cell rules cannot read (`21.5%`): a labelled line, not a header,
    # whose last cell holds a digit and no letter.
    cells = [cell.group() for cell in _CELL.finditer(read)]
    return (
        len(cells) >= 2
        and not _is_header(line)
        and _WORD.search(cells[0]) is not None
        and any(c.isdigit() for c in cells[-1])
        and _WORD.search(cells[-1]) is None
    )


def _label_ends_numeric(label: str) -> bool:
    tokens = label.split()
    return bool(tokens) and _NUMERIC_CELL.fullmatch(tokens[-1]) is not None


def _flags(line: ExtractedLine, years: int, footnote: bool) -> tuple[LineFlag, ...]:
    flags: list[LineFlag] = []
    if years and len(line.raw_values) > years:
        flags.append(MORE_VALUES_THAN_HEADER_YEARS)
    if _label_ends_numeric(line.label):
        flags.append(LABEL_ENDS_NUMERIC)
    if footnote:
        flags.append(FOOTNOTE_MARKER)
    return tuple(flags)


@dataclass(frozen=True)
class _Table:
    """The header block over a run of data lines: its year count, the column where the year
    line's first year starts, whether it names a Note column left of it, and the 0-based line
    where that Note column ends."""

    years: int = 0
    year_column: int | None = None
    note_header: bool = False
    note_until: int = 0


def _table(lines: Sequence[str], first: int, data_at: Collection[int]) -> _Table:
    """The table whose first data line is the 0-based line `first` (module docstring)."""
    headers = [_unpipe(lines[index]) for index in _header_indexes(lines, first, data_at)]
    # The year line: the header line nearest the data holding two or more years, else one.
    ranked = [(min(len(_YEAR.findall(header)), 2), at) for at, header in enumerate(headers)]
    count, at = max(ranked, default=(0, 0))
    year = _YEAR.search(headers[at]) if count else None
    if year is None:
        return _Table(note_until=len(lines))
    note_until = next(
        (i for i in range(first, len(lines)) if i not in data_at and _is_header(lines[i])),
        len(lines),
    )
    return _Table(
        years=len(_YEAR.findall(headers[at])),
        year_column=year.start(),
        note_header=any(
            _NOTE_HEADER.fullmatch(cell.group()) and cell.start() < year.start()
            for header in headers
            for cell in _CELL.finditer(header)
        ),
        note_until=note_until,
    )


def _tables(lines: Sequence[str], rows: Sequence[int]) -> list[_Table]:
    """The table of each data line (0-based `rows`, in page order): a period row between two
    data lines starts a new table with its own header block."""
    data_at = frozenset(rows)
    tables: list[_Table] = []
    previous = -1
    for row in rows:
        if not tables or any(_is_period_row(lines[i]) for i in range(previous + 1, row)):
            tables.append(_table(lines, row, data_at))
        else:
            tables.append(tables[-1])
        previous = row
    return tables


def _footnote_marker(line: ExtractedLine, cells: _Cells, table: _Table, note_column: bool) -> bool:
    """The first cell is a footnote marker `(n)` or, under a "Note" header, a bare note reference:
    left of the first year column, and the one value more than the years that makes it a
    reference."""
    first = line.raw_values[0]
    return (
        table.years > 0
        and table.year_column is not None
        and cells.first_end < table.year_column
        and len(line.raw_values) == table.years + 1
        and not cells.first_dollar
        and (
            _FOOTNOTE.fullmatch(first) is not None
            or (note_column and _BARE_REF.fullmatch(first) is not None)
        )
    )


def _note_reference(cells: _Cells, table: _Table, note_column: bool) -> bool:
    """The label ends in a several-number note reference (`7 and 9`) under a "Note" header that
    counts as the extra cell: left of the first year column, with exactly the years' values
    after it."""
    return (
        note_column
        and table.years > 0
        and table.year_column is not None
        and cells.note_head is not None
        and cells.note_end < table.year_column
        and len(cells.raw_values) == table.years
    )


def _bare_note_number(line: ExtractedLine, cells: _Cells, table: _Table) -> bool:
    """Under a Note column, an unsigned bare first number of one or two digits left of the
    years, with a sign folded into a later cell, is label text."""
    return (
        cells.later_sign
        and not cells.first_dollar
        and table.year_column is not None
        and cells.first_end < table.year_column
        and len(line.raw_values) == table.years
        and _BARE_REF.fullmatch(line.raw_values[0]) is not None
    )


def _drop_first(line: ExtractedLine) -> ExtractedLine:
    return replace(
        line,
        raw_values=line.raw_values[1:],
        values=line.values[1:],
        currency_values=line.currency_values[1:],
    )


def _finish(line: ExtractedLine, cells: _Cells, table: _Table) -> tuple[ExtractedLine, str]:
    """The data line with a footnote marker, note reference or bare note number resolved and
    its flags set, and the part of its label printed on its own line."""
    note_column = table.note_header and line.line_no - 1 < table.note_until
    if _footnote_marker(line, cells, table, note_column):
        data = _drop_first(line)
        return replace(data, flags=_flags(data, table.years, True)), cells.label
    if cells.note_head is not None and _note_reference(cells, table, note_column):
        head = line.label.removesuffix(cells.label).rstrip()
        data = replace(line, label=" ".join(filter(None, (head, cells.note_head))))
        return replace(data, flags=_flags(data, table.years, True)), cells.note_head
    if note_column and _bare_note_number(line, cells, table):
        own = f"{cells.label} {line.raw_values[0]}"
        data = replace(_drop_first(line), label=f"{line.label} {line.raw_values[0]}")
        return replace(data, flags=_flags(data, table.years, False)), own
    return replace(line, flags=_flags(line, table.years, False)), cells.label


def _read_rows(lines: Sequence[str], locator: str) -> list[tuple[ExtractedLine, _Cells]]:
    """Each printed data line, unflagged, with its parsed cells, in page order."""
    found: list[tuple[ExtractedLine, _Cells]] = []
    caption: str | None = None
    pending: list[str] = []  # continuation lines directly above the current line
    for index, line in enumerate(lines):
        stripped = line.strip()
        cells = _cells(line)
        if cells is not None:
            head = pending[0] if pending else line
            printed = ExtractedLine(
                locator=locator,
                line_no=index + 1,
                label=" ".join((*(part.strip() for part in pending), cells.label)),
                raw_values=cells.raw_values,
                values=cells.values,
                indent=len(head) - len(head.lstrip()),
                caption=caption,
                currency_values=cells.currency_values,
            )
            found.append((printed, cells))
            pending = []
        elif _is_caption(stripped):
            caption = stripped
            pending = []
        elif _is_continuation(stripped):
            pending.append(line)
        else:
            pending = []
    return found


def extract_statement_lines(
    text: str, locator: str, source_id: str | None = None
) -> ExtractedTable:
    """The printed data lines of one page's text (module docstring rules); prose yields none."""
    lines = [line.removesuffix("\r") for line in text.split("\n")]
    found = _read_rows(lines, locator)
    rows = [printed.line_no - 1 for printed, _ in found]
    header_at = _header_indexes(lines, rows[0]) if rows else ()
    boundaries = set(header_at)
    boundaries.update(index for index, line in enumerate(lines) if _is_period_header(line))
    finished: list[ExtractedLine] = []
    for (printed, cells), table in zip(found, _tables(lines, rows), strict=True):
        data, own_label = _finish(printed, cells, table)
        candidates = _label_candidates(lines, printed.line_no - 1, own_label, boundaries)
        finished.append(replace(data, label_candidates=candidates))
    kept = set(rows).union(header_at)
    return ExtractedTable(
        locator=locator,
        headers=tuple(lines[index] for index in header_at),
        lines=tuple(finished),
        source_id=source_id,
        omitted=tuple(
            OmittedLine(line_no=index + 1, text=text)
            for index, text in enumerate(lines)
            if index not in kept and _is_omitted_candidate(text)
        ),
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
