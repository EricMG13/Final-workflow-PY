"""Statement rows from HTML line sources (CP1H-R18 rows, option iii).

`convert_html` writes one table row per line, its cells joined by single spaces. DVII's extractor
reads cells separated by two spaces, so on such a line it finds no row. `respace` re-spaces a
line's trailing money and number tokens (and header phrases) into cells using only the line text;
nothing is read from the raw bytes. `line_table` is DVII's range logic over respaced lines, and
`LineTools` and `seen_tables` serve it to the extract tool and the validators. DVII is not
modified or patched; its public `extract_statement_lines` does the extraction.

Label rule: each row's label is its own line's label cell. DVII merges a value-less, colon-less
line onto the next row's label; in an HTML line source each table row is one line, so that merge
only glues a heading row onto an unrelated row, and `line_table` undoes it.
"""

import re
from collections.abc import Mapping
from dataclasses import replace
from itertools import pairwise

from deploy_vii.contracts import Span
from deploy_vii.live.prompts import block
from deploy_vii.live.tools import (
    MAX_LINES_PER_EXTRACT,
    MAX_PAGES_PER_EXTRACT,
    PackTools,
    Seen,
    ToolError,
    extracted_body,
)
from deploy_vii.live.tools import seen_tables as dvii_seen_tables
from deploy_vii.source_context import SourceContextReview
from deploy_vii.statement_extract import (
    ExtractedLabelPart,
    ExtractedTable,
    extract_statement_lines,
)

_NUMBER = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
# The currency symbols the extractor reads (`statement_extract._SIGNS`): `$`, `€`, `£`.
_CURRENCY = frozenset("$€£")
_NUMTOK = re.compile(rf"[$€£]?(?:\((?:{_NUMBER})\)|−?(?:{_NUMBER})|—|–|-)")
# An EDGAR split parenthesis: `<td>(250</td><td>)</td>` converts to the tokens `(250` and `)`.
_OPEN_PAREN = re.compile(rf"[$€£]?\((?:{_NUMBER})")
# A value cell the extractor cannot read: a split parenthesis `(250 )` or a Unicode minus `−45`.
_UNREADABLE = re.compile(r"\(\S+ \)|−")
_YEAR = re.compile(r"(?:19|20)\d\d")
_DAY = r"\d\d?"
_WORD = re.compile(r"[A-Za-z]+")
_YEAR_IN_TEXT = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_MONTH_NAMES = [
    *("January", "February", "March", "April", "May", "June", "July", "August"),
    *("September", "October", "November", "December"),
]
_MONTHS = frozenset((*_MONTH_NAMES, *(name.upper() for name in _MONTH_NAMES)))
_HEADWORDS = frozenset(
    (
        *(name.lower() for name in _MONTH_NAMES),
        *("three", "six", "nine", "twelve", "fiscal", "year", "years"),
    )
)
_HCELL = re.compile(
    rf"(?:Three|Six|Nine|Twelve) Months Ended [A-Z][a-z]+ {_DAY},?"
    rf"|(?:Fiscal )?Years? Ended [A-Z][a-z]+ {_DAY},?"
    rf"|[A-Z][a-z]+ {_DAY}, (?:19|20)\d\d"
    rf"|[A-Z][a-z]+ {_DAY},?(?= |$)"
    r"|(?:19|20)\d\d",
    re.IGNORECASE,
)
_LINE_RANGE = re.compile(r"line:([1-9][0-9]{0,8})-([1-9][0-9]{0,8})")
_CELL_GAP = "  "


def _is_header(line: str) -> bool:
    return len(_YEAR_IN_TEXT.findall(line)) >= 2 or bool(_MONTHS.intersection(_WORD.findall(line)))


def _header_cells(line: str) -> str | None:
    """A header line split into its leading label and period cells, or None if it holds other text."""
    found = [
        m
        for m in _HCELL.finditer(line)
        if m.group().split()[0].lower() in _HEADWORDS or _YEAR.fullmatch(m.group())
    ]
    if not found:
        return None
    gaps = [line[a.end() : b.start()] for a, b in pairwise(found)]
    gaps.append(line[found[-1].end() :])
    if any(gap.strip() for gap in gaps):
        return None
    lead = line[: found[0].start()].strip()
    return _CELL_GAP.join(([lead] if lead else []) + [m.group() for m in found])


def _split(tokens: list[str]) -> tuple[int, list[str]]:
    """The trailing value cells of a line's space-split tokens, last first, and the index where
    they start: money and number tokens, a bare `$`, `€` or `£` folded into the cell to its
    right, and a bare `)` folded onto the `(N` token to its left (an EDGAR split parenthesis)."""
    values: list[str] = []
    index = len(tokens)
    while index > 0:
        token = tokens[index - 1]
        if token in _CURRENCY and values and values[-1][0] not in _CURRENCY:
            values[-1] = f"{token} {values[-1]}"
            index -= 1
            continue
        if token == ")" and index >= 2 and _OPEN_PAREN.fullmatch(tokens[index - 2]):
            values.append(f"{tokens[index - 2]} )")
            index -= 2
            continue
        if _NUMTOK.fullmatch(token):
            if (
                _YEAR.fullmatch(token)
                and index >= 2
                and not _NUMTOK.fullmatch(tokens[index - 2])
                and tokens[index - 2] not in _CURRENCY
            ):
                break
            values.append(token)
            index -= 1
            continue
        break
    return index, values


def _unreadable_cells(line: str) -> list[str]:
    """The trailing value cells of a line that the extractor cannot read (`_UNREADABLE`), in line
    order; empty for any other line. One such cell is enough: `(250 )` or `−45` is a value."""
    _, values = _split(line.split(" "))
    return [cell for cell in reversed(values) if _UNREADABLE.search(cell)]


def respace(line: str) -> str:
    """`line` with its trailing money and number tokens as cells joined by two spaces.

    A bare 19xx/20xx with no comma or `$`, whose left neighbour is not a number, ends the label
    (it is a year in the label, `in 2023`, not a value). A line of period phrases is split into
    header cells. Any other line is returned unchanged. Only spacing changes: splitting on
    whitespace gives the same tokens, and no newline is added or removed."""
    tokens = line.split(" ")
    index, values = _split(tokens)
    if len(values) >= 2:
        label = " ".join(tokens[:index])
        header = _header_cells(line) if not label or _is_header(line) else None
        if header is not None and all(_YEAR.fullmatch(value) for value in values):
            return header
        return _CELL_GAP.join(([label] if label else []) + list(reversed(values)))
    if _is_header(line):
        header = _header_cells(line)
        if header is not None:
            return header
    return line


def _range_of(item: str) -> tuple[int, int]:
    match = _LINE_RANGE.fullmatch(item)
    if match is None:
        raise ToolError(f"bad arguments: {item} is not a line:N-M range")
    return int(match.group(1)), int(match.group(2))


def line_table(spans: Mapping[int, Span], item: str, source_id: str) -> ExtractedTable:
    """The table of the range `item` (`line:N-M`) of a line source: each span's text respaced,
    joined by newlines and extracted as one text, each row rebased to its own `line:K`, and its
    label set to its own line's label cell. A missing line or a span holding a newline is a
    refused call."""
    first, last = _range_of(item)
    texts = []
    for number in range(first, last + 1):
        span = spans.get(number)
        if span is None:
            raise ToolError(f"line:{number} is not a located span of {source_id}")
        if "\n" in span.text:
            raise ToolError(f"line:{number} of {source_id} holds a newline and cannot be ranged")
        if unreadable := _unreadable_cells(span.text):
            # Fail closed: the extractor would drop the line (or read it without these cells)
            # and a negative row such as an operating loss would vanish without a flag.
            cells = ", ".join(repr(cell) for cell in unreadable)
            raise ToolError(
                f"line:{number} of {source_id} holds value cells Python cannot read ({cells}: "
                "a split parenthesis or a Unicode minus); the range is refused rather than "
                "extracted without the line"
            )
        texts.append(respace(span.text))
    table = extract_statement_lines("\n".join(texts), item, source_id=source_id)
    rows = []
    for line in table.lines:
        own = texts[line.line_no - 1].split(_CELL_GAP)[0].strip()
        # DVII prefixes continuation lines onto `label`, so the row's own label ends it. A label
        # that does not end with it (a pipe in the text was read as a cell gap) stays as DVII
        # read it.
        label = own if own and line.label.endswith(own) else line.label
        number = first + line.line_no - 1
        rows.append(
            replace(
                line,
                label=label,
                line_no=number,
                locator=f"line:{number}",
                label_candidates=(
                    *(
                        ExtractedLabelPart(line_no=first + part.line_no - 1, text=part.text)
                        for part in line.label_candidates[:-1]
                        if part.text.rstrip().endswith(":")
                    ),
                    ExtractedLabelPart(line_no=number, text=label),
                ),
            )
        )
    source_lines = tuple(
        replace(line, line_no=first + line.line_no - 1) for line in table.source_lines
    )
    return replace(table, lines=tuple(rows), source_lines=source_lines)


class LineTools(PackTools):
    """`PackTools` whose `extract_statements` serves line sources through `line_table`."""

    def _extract_lines(self, source_id: str, locators: object) -> str:
        if not isinstance(locators, list) or not all(
            isinstance(item, str) and _LINE_RANGE.fullmatch(item) for item in locators
        ):
            raise ToolError("bad arguments: locators must be a list of line:N-M ranges")
        if not locators:
            raise ToolError("bad arguments: locators must name at least one range")
        if len(locators) > MAX_PAGES_PER_EXTRACT:
            raise ToolError(f"bad arguments: at most {MAX_PAGES_PER_EXTRACT} ranges per call")
        if repeated := sorted({item for item in locators if locators.count(item) > 1}):
            raise ToolError(f"bad arguments: locators repeat {', '.join(repeated)}")
        covered = 0
        for item in locators:
            first, last = _range_of(item)
            if last < first:
                raise ToolError(f"bad arguments: {item} runs backwards")
            covered += last - first + 1
        if covered > MAX_LINES_PER_EXTRACT:
            raise ToolError(f"bad arguments: at most {MAX_LINES_PER_EXTRACT} lines per call")
        tables = [line_table(self.lines[source_id], item, source_id) for item in locators]
        digest = str(self.ready[source_id].sha256)
        parts = [block("SOURCE", source_id, digest, extracted_body(table)) for table in tables]
        for table in tables:
            self.extracted.add((source_id, table.locator))
            self.extracted.update((source_id, line.locator) for line in table.lines)
        return "\n".join(parts)


def seen_tables(
    tools: PackTools, seen: Seen, context: SourceContextReview
) -> tuple[ExtractedTable, ...]:
    """DVII's `seen_tables`, with each line source's tables replaced by `line_table`'s. Page
    sources come from DVII (given a `Seen` without line ranges, so it builds none for a line
    source); the result keeps DVII's pack order."""
    financial = {item.source_id for item in context.sources if item.classification == "financial"}
    pages = dvii_seen_tables(
        tools,
        Seen(
            frozenset(
                (ident, loc)
                for ident, loc in seen.read
                if not (ident in tools.lines and _LINE_RANGE.fullmatch(loc))
            ),
            seen.searched,
        ),
        context,
    )
    tables: list[ExtractedTable] = []
    for source_id in tools.ready:
        if source_id not in financial:
            continue
        if source_id in tools.lines:
            ranges = sorted(
                (
                    loc
                    for ident, loc in seen.read
                    if ident == source_id and _LINE_RANGE.fullmatch(loc)
                ),
                key=_range_of,
            )
            tables += [line_table(tools.lines[source_id], loc, source_id) for loc in ranges]
        else:
            tables += [table for table in pages if table.source_id == source_id]
    return tuple(tables)
