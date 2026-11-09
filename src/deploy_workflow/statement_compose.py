"""The statement composer (CP1H-R23, change 1, part a): Python writes the statement lines.

The model maps a located statement unit; Python writes every line of it. The model supplies
(R23.1) one period id or None per column, and per row the four judgment fields (`line_id`,
`item_id`, `line_kind`, `sign_convention`). `compose_unit` then writes, for each mapped row and
each column that maps a declared period, one real deploy_vii `StatementLine`:

- `statement` is the unit's kind, `label` the row label as extracted, `period_id` the column's;
- `amount` is the extractor's own parsed value of the printed cell (`ExtractedLine.values`, from
  `statement_extract`'s one raw-value parser); a printed nil dash (None) is 0;
- the citation is `source_id`, the row's own locator (`line:N` on a line source, the page on a
  page source) and the row label as the quote;
- `display_priority` is the row's position in the unit (plus `priority_offset`);
- `observation_id` is `<line_id>.<period_id>`, so it is unique per line;
- `sign_citations` is that same citation where the row map says `outflow_magnitude`.

Python never picks a period (R23.2): a None column gets no line, and a column map that repeats a
period is refused. Rows left to the model (R23.3), each with its reason: a flagged row, a row
whose value count differs from the unit's column count, a row absent from the row map, a row-map
entry naming a row the unit does not have (`no_such_row`), a row-map entry that is not four fields
(`bad_row_map_entry`), a row the contract refuses (`refused_by_contract`), a row number the unit
repeats (`repeated_row_number`), a row whose caption names another statement than the unit's
(`other_statement`, R23.22; the caller supplies these). "Flagged" (R23.13) means a flag that casts doubt on the values,
`label_ends_numeric`, `more_values_than_header_years` or `ambiguous_separator`;
`footnote_marker` is informational (the
marker is already dropped and the values are clean), so a row whose only flag it is is composed.

Before composing (R23.4) the totals the row map identifies are checked per mapped column, in
Decimal. A CFS row the row map says is `outflow_magnitude` enters the check as -abs(cell), as
the book reads it (`financial_reconciliation`). If a check fails nothing is composed for the unit
and the issue names the check, the column and both sums. Where the rows are not identified the
unit is composed and `Composition.checks_not_applied` says which check was not applied and why.

A unit on a page read by OCR (`ocr=True`, R23.23) is composed only when at least one check was
applied, none was left unapplied and none failed. Otherwise every row it would have composed is
left to the model with `OCR_UNCHECKED`: OCR digits are not trusted without the arithmetic.

On a page that prints a note-reference column (`note_page=True`, R23.24) a row whose first
printed value is a bare unsigned 1-2-digit number or `n.n` may be a note number the extractor did
not drop: it is left to the model with `NOTE_SUSPECT`, and the gate still requires its coverage.
So is a row in `note_rows` (R23.24.1: below a second header of the page, where the extractor
dropped a note that may have been a value).

Pure: no I/O, no model call, no global state.
"""

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from itertools import pairwise
from types import MappingProxyType
from typing import Any, Literal, NamedTuple

from pydantic import ValidationError

from deploy_vii.financial_contracts import (
    FinancialBook,
    StatementLabelPart,
    StatementLine,
    StatementQuantity,
    statement_dimensions,
)
from deploy_vii.statement_extract import FOOTNOTE_MARKER, ExtractedLine, ExtractedTable

Kind = Literal["BS", "IS", "CFS"]
_LABEL_WORD = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class ResolvedLabel:
    """A source-derived label and its ordered, exact fragments."""

    label: str
    parts: tuple[StatementLabelPart, ...]


@dataclass(frozen=True)
class ResolvedTypedRow:
    """The exact selected label and its source-verified quantity family."""

    label: ResolvedLabel
    quantity: StatementQuantity
    family: Literal["monetary", "currency_per_share", "shares"]


def resolve_label_parts(
    table: ExtractedTable, row: ExtractedLine, part_line_numbers: Sequence[int]
) -> ResolvedLabel | None:
    """Resolve a complete row label, allowing only proven leading section context to be omitted."""
    if not part_line_numbers or part_line_numbers[-1] != row.line_no:
        return None
    if tuple(sorted(set(part_line_numbers))) != tuple(part_line_numbers):
        return None
    candidates: dict[int, str] = {}
    for part in row.label_candidates:
        if part.line_no in candidates:
            return None
        candidates[part.line_no] = part.text
    if any(number not in candidates for number in part_line_numbers):
        return None
    for left, right in pairwise(part_line_numbers):
        if right != left + 1 and not (
            candidates[left].rstrip().endswith(":")
            and right == row.line_no
            and re.fullmatch(r"(?:Basic|Diluted)(?: and diluted)?", row.label, re.IGNORECASE)
            and _local_quantity_family(candidates[left]) in {"shares", "currency_per_share"}
        ):
            return None
    selected = set(part_line_numbers)
    candidate_parts = row.label_candidates
    first_selected = next(
        (index for index, part in enumerate(candidate_parts) if part.line_no in selected),
        len(candidate_parts),
    )
    for index, part in enumerate(candidate_parts[:first_selected]):
        if part.line_no in selected or part.text.rstrip().endswith(":"):
            continue
        # Uppercase section captions such as ASSETS may precede a more specific colon heading.
        # Without that structural signal, an unpunctuated fragment is part of the row identity.
        words = _LABEL_WORD.findall(part.text)
        followed_by_heading = index + 1 < first_selected and candidate_parts[
            index + 1
        ].text.rstrip().endswith(":")
        if not (words and not any(char.islower() for char in part.text) and followed_by_heading):
            return None
    last_heading = max(
        (index for index, part in enumerate(candidate_parts) if part.text.rstrip().endswith(":")),
        default=-1,
    )
    required = tuple(part.line_no for part in candidate_parts[last_heading + 1 :])
    if any(number not in selected for number in required):
        return None
    line_table = table.locator.startswith("line:")
    parts = tuple(
        StatementLabelPart(
            locator=f"line:{number}" if line_table else row.locator,
            line_no=number,
            text=candidates[number],
        )
        for number in part_line_numbers
    )
    return ResolvedLabel(" ".join(part.text for part in parts), parts)


def resolve_typed_row(
    table: ExtractedTable,
    row: ExtractedLine,
    *,
    part_line_numbers: Sequence[int],
    source_id: str,
    source_sha256: str,
    quantity: StatementQuantity,
    book_currency: str,
    book_unit: str,
    context_tables: Sequence[ExtractedTable] | None = None,
) -> ResolvedTypedRow | None:
    """Resolve exact parts and the row's one source-supported quantity family, or refuse it."""
    resolved = resolve_label_parts(table, row, part_line_numbers)
    if not table.source_lines or not quantity.citations:
        return None
    if resolved is None:
        return None
    # A unit's dimensional evidence belongs to that unit. A matching quote elsewhere
    # in the same filing cannot supply its scale or currency.
    first_row = min((item.line_no for item in table.lines), default=row.line_no)
    header = tuple(item for item in table.source_lines if item.line_no < first_row)
    data_rows = {item.line_no for item in table.lines}
    evidence_lines = tuple(
        item for item in table.source_lines
        if item.line_no <= row.line_no and (item.line_no not in data_rows or item.line_no == row.line_no)
    )
    contexts: list[str] = []
    for citation in quantity.citations:
        if citation.source_id != source_id or citation.source_sha256 != source_sha256:
            return None
        if citation.locator.startswith("page:"):
            matched = table.locator == citation.locator and any(
                citation.quote in source_line.text for source_line in evidence_lines
            )
        else:
            match = re.fullmatch(r"line:(\d+)", citation.locator)
            matched = match is not None and any(
                source_line.line_no == int(match[1]) and citation.quote in source_line.text
                for source_line in evidence_lines
            )
        if not matched:
            return None
        # Read the complete source header, not a substring chosen by the model.
        contexts.append(" ".join(item.text for item in header).casefold())
    context = " ".join(dict.fromkeys(contexts))
    selected_family = _local_quantity_family(resolved.label)
    bounded_family = _local_quantity_family(" ".join(p.text for p in row.label_candidates))
    if (
        selected_family is None
        or selected_family != bounded_family
        or quantity.kind != selected_family
    ):
        return None
    own_line = next((item.text for item in table.source_lines if item.line_no == row.line_no), "")
    if not _currency_matches(book_currency, context + " " + own_line):
        return None
    if selected_family == "currency_per_share":
        supported = (
            quantity.scale == "UNITS"
            and bool(book_currency)
            and re.search(r"\bper\s+(?:(?:common|ordinary)\s+)?share\b", context) is not None
        )
    elif selected_family == "shares":
        supported = not any(row.currency_values) and quantity.scale == _header_scale(context, True)
    else:
        supported = quantity.scale == book_unit == _header_scale(context, False)
    return ResolvedTypedRow(resolved, quantity, selected_family) if supported else None


def _header_scale(context: str, shares: bool) -> str | None:
    """Resolve an explicit header's family-specific scale, refusing conflicting cues."""
    share_clause = re.search(r"\bshares?\s+(not\s+)?in\s+(thousands?|millions?|units?)\b", context)
    if shares and share_clause:
        return "UNITS" if share_clause[1] else share_clause[2].upper().rstrip("S") + "S"
    if shares and (excepted := _shares_excepted(context)) is not None:
        # an except clause that also scales them is ambiguous: refuse rather than guess
        return "UNITS" if excepted else None
    # A per-share exception alone does not except share counts from the monetary scale.
    text = (
        context
        if share_clause is None
        else context[: share_clause.start()] + context[share_clause.end() :]
    )
    scales = {
        name
        for name, pattern in (
            ("UNITS", r"\bunits?\b"),
            ("THOUSANDS", r"\bthousands?\b|\b000s\b"),
            ("MILLIONS", r"\bmillions?\b"),
        )
        if re.search(pattern, text)
    }
    return next(iter(scales)) if len(scales) == 1 else None


_EXCEPT_CLAUSE = re.compile(r"\bexcept\s+(?:for\s+)?([^;()|]{0,80}?)(?=[;()|]|\s{2,}|$)")
_PER_SHARE = re.compile(r"\bper[\s-]+(?:(?:common|ordinary)\s+)?shares?\b")
_ITEM_GAP = re.compile(r"\s*(?:,|&|/|\band\b|\bor\b)\s*")
# An item of an except clause that begins with a share count: "share data", "number of shares",
# "share counts in millions". A share word that does not begin an item ("per share data shares
# outstanding", the column heading joined after the clause) names no share count; neither do share
# price, capital, premium and value.
_SHARE_ITEM = re.compile(
    r"(?:the\s+)?(?:(?:weighted[\s-]average|average|total|basic|diluted)\s+)*(?:number\s+of\s+)?"
    r"(?:(?:common|ordinary)\s+)?shares?\b(?!\s+(?:price|capital|premium|value)\b)"
)


def _shares_excepted(context: str) -> bool | None:
    """True when an "except ..." clause names share counts as one of its items ("except share
    data", "except per share and share data", "... and number of shares", "... and share
    counts"); False when that clause also names a scale ("... and share counts in millions");
    else None, and share counts take the monetary scale. A per-share item alone names no share
    count, and neither does a share word that is not an item of its own."""
    for clause in _EXCEPT_CLAUSE.findall(context):
        items = _ITEM_GAP.split(_PER_SHARE.sub(" ", clause).strip())
        if any(_SHARE_ITEM.match(item) for item in items):
            return re.search(r"thousand|million|billion|\b000s\b", clause) is None
    return None


# A bare "$" names no currency. Only a USD book reads it as its own: on any other book, a dollar
# sign that does not say which dollar could be a US dollar amount (S11-A06).
_BARE_DOLLAR = re.compile(r"(?<![A-Za-z$])\$")


def _currency_matches(book_currency: str, text: str) -> bool:
    """Whether the stated currency of a header or row text is the book's. A word, an ISO code or a
    prefixed symbol ("US$", "C$", "CA$", "A$", "EUR", "€", "£") states a currency; a bare "$"
    states none, and with nothing else stated it verifies only a USD book."""
    declared = {
        code
        for code, pattern in (
            ("EUR", r"€|\beuros?\b|\bEUR\b"),
            ("GBP", r"£|\bpounds?\b|\bGBP\b"),
            (
                "USD",
                r"\bUSD\b|\bU\.?S\.?\s+dollars?\b|\bUnited\s+States\s+dollars?\b|\bU\.?S\.?\s?\$",
            ),
            ("CAD", r"\bCAD\b|\bCanadian\s+dollars?\b|\bC(?:A)?\$"),
            ("AUD", r"\bAUD\b|\bAustralian\s+dollars?\b|\bA\$"),
        )
        if re.search(pattern, text, re.IGNORECASE)
    }
    if book_currency and not declared and _BARE_DOLLAR.search(text):
        return book_currency == "USD"
    return not declared or declared == {book_currency}


_SHARE_COUNT_HEAD = re.compile(
    r"^\s*(?:(?:weighted[ -]+average|average(?:\s+number\s+of)?|number\s+of|"
    r"total|basic|diluted|issued|outstanding)(?:\s+(?:and|or))?\s+)*"
    r"(?:class\s+[A-Za-z]\s+)?(?:(?:common|ordinary)\s+)?shares\b",
    re.IGNORECASE,
)


def _share_count_label(label: str) -> bool:
    """Whether the row's leading noun phrase names a share count (not stock carrying a count)."""
    return _SHARE_COUNT_HEAD.search(label) is not None


def _unresolved_leading_count_intent(label: str) -> bool:
    """Refuse an authorized-share fragment whose leading count meaning is incomplete."""
    return (
        re.match(r"^\s*authorized\b", label, re.IGNORECASE) is not None
        and re.search(r"\bshares\b", label, re.IGNORECASE) is not None
        and not _share_count_label(label)
    )


def _local_quantity_family(
    label: str | ResolvedLabel,
) -> Literal["monetary", "currency_per_share", "shares"] | None:
    text = label.label if isinstance(label, ResolvedLabel) else label
    per_share = re.search(r"\bper\s+(?:(?:common|ordinary)\s+)?share\b", text, re.IGNORECASE) is not None
    shares = _share_count_label(text)
    unresolved_count = _unresolved_leading_count_intent(text)
    if unresolved_count or (per_share and shares):
        return None
    if per_share:
        return "currency_per_share"
    if shares:
        return "shares"
    return "monetary"


def source_quantity_family(
    table: ExtractedTable, row: ExtractedLine, label: str | None = None
) -> Literal["monetary", "currency_per_share", "shares"] | None:
    """Bare Basic/Diluted rows inherit their nearest local, non-data heading."""
    text = row.label if label is None else label
    family = _local_quantity_family(text)
    if not re.fullmatch(r"\s*(?:basic|diluted)(?:\s+and\s+diluted)?\s*", text, re.IGNORECASE):
        return family
    data_lines = {item.line_no for item in table.lines}
    for item in reversed(table.source_lines):
        if item.line_no >= row.line_no or item.line_no in data_lines or not item.text.strip():
            continue
        heading_family = _local_quantity_family(item.text)
        return heading_family if heading_family in {"shares", "currency_per_share"} else None
    return None


def _typed_row_resolution(
    table: ExtractedTable,
    row: ExtractedLine,
    source_id: str,
    source_sha256: str,
    row_label_selections: Mapping[int, Sequence[int]],
    row_dimensions: Mapping[int, StatementQuantity],
    book_currency: str,
    book_unit: str,
    context_tables: Sequence[ExtractedTable] | None,
) -> ResolvedTypedRow | None:
    quantity = row_dimensions.get(row.line_no)
    if quantity is None:
        return None
    return resolve_typed_row(
        table,
        row,
        part_line_numbers=row_label_selections.get(row.line_no, ()),
        source_id=source_id,
        source_sha256=source_sha256,
        quantity=quantity,
        book_currency=book_currency,
        book_unit=book_unit,
        context_tables=context_tables,
    )


def validate_typed_statement_line(
    table: ExtractedTable,
    row: ExtractedLine,
    line: StatementLine,
    book: FinancialBook,
    source_sha256: str,
    context_tables: Sequence[ExtractedTable] | None = None,
) -> bool:
    """Re-resolve typed labels and dimensions against the current extraction for the gate."""
    if line.quantity is None or line.label_parts is None:
        return False
    numbers = tuple(part.line_no for part in line.label_parts)
    resolution = resolve_typed_row(
        table,
        row,
        part_line_numbers=numbers,
        source_id=table.source_id or "",
        source_sha256=source_sha256,
        quantity=line.quantity,
        book_currency=book.currency,
        book_unit=book.unit,
        context_tables=context_tables,
    )
    if (
        resolution is None
        or line.label != resolution.label.label
        or line.label_parts != resolution.label.parts
    ):
        return False
    expected = {
        (table.source_id, source_sha256, part.locator, part.text) for part in resolution.label.parts
    }
    cited = {
        (citation.source_id, citation.source_sha256, citation.locator, citation.quote)
        for citation in line.value.citations
    }
    if not expected.issubset(cited):
        return False
    dimensions = statement_dimensions(book, line)
    return (
        dimensions.kind == line.quantity.kind
        and dimensions.scale == line.quantity.scale
        and dimensions.currency == (None if line.quantity.kind == "shares" else book.currency)
    )


# Reasons a row is left to the model (R23.3).
FLAGGED = "flagged"
VALUE_COUNT = "value_count"
NOT_IN_ROW_MAP = "not_in_row_map"
NO_SUCH_ROW = "no_such_row"
REFUSED = "refused_by_contract"
REPEATED_ROW = "repeated_row_number"
BAD_ENTRY = "bad_row_map_entry"
UNIT_CHECK_FAILED = "unit_check_failed"
OTHER_STATEMENT = "other_statement"
OCR_UNCHECKED = "ocr_unchecked"
NOTE_SUSPECT = "note_reference_suspect"
NOTE_SUSPECT_DETAIL = (
    "the page prints a note-reference column and this row's first value could be a note number; "
    "Python writes no line for it"
)
NOTE_BELOW_HEADER_DETAIL = (
    "the page prints a note-reference column and this row sits below a second header, so its "
    "dropped note may have been a value; Python writes no line for it"
)
_NOTE_LOOKING = re.compile(r"\d{1,2}(?:\.\d{1,2})?")
OCR_UNCHECKED_DETAIL = (
    "the page was read by OCR and Python could not verify this unit (its arithmetic checks or "
    "its period header); Python writes no line for it and coverage does not require it"
)

# The item ids the checks read (statement_validation's REQUIRED_ITEMS / OPTIONAL_ITEMS). The
# printed "total liabilities and equity" has no standard id: the model gives that row this
# `other:` id.
TOTAL_ASSETS = "total_assets"
TOTAL_LIABILITIES = "total_liabilities"
TOTAL_EQUITY = "total_equity"
TOTAL_LIABILITIES_AND_EQUITY = "other:total_liabilities_and_equity"
OPERATING = "cfo_ncfo"
INVESTING = "investing_cash_flow"
FINANCING = "financing_cash_flow"
FX_EFFECT = "fx_cash_effect"
NET_CHANGE = "net_cash_change"

BS_LIABILITIES_PLUS_EQUITY = "bs_assets_eq_liabilities_plus_equity"
BS_PRINTED_TOTAL = "bs_assets_eq_printed_liabilities_and_equity"
CFS_NET_CHANGE = "cfs_sections_eq_net_change"
COLUMN_MAP_DISTINCT = "column_map_distinct"
SOURCE_LABEL_REFUSED = "source_label_refused"
SOURCE_QUANTITY_REFUSED = "source_quantity_refused"


class RowJudgment(NamedTuple):
    """The model's four judgment fields for one row."""

    line_id: str
    item_id: str
    line_kind: Literal["detail", "subtotal", "total"]
    sign_convention: Literal["signed", "outflow_magnitude"]


@dataclass(frozen=True)
class LeftToModel:
    """A row Python did not compose. `line_no` is the row number (for `NO_SUCH_ROW`, the number
    the row map named); `locator` and `label` are the row's, empty where the unit has no such
    row."""

    line_no: int
    locator: str
    label: str
    reason: str
    detail: str


@dataclass(frozen=True)
class CheckIssue:
    """A failed check (R23.4): `column` is the 0-based column, `period_id` its mapped period,
    `lhs` and `rhs` the two sums."""

    check: str
    column: int
    period_id: str | None
    lhs: Decimal | None
    rhs: Decimal | None
    message: str


@dataclass(frozen=True)
class Composition:
    """What `compose_unit` returns. `checks_not_applied` holds `(check, why)` for each check the
    row map did not identify the rows for; `undeclared` holds `(column, period_id)` for each
    column the model mapped to an id that is not a declared period (no line is written)."""

    lines: tuple[StatementLine, ...]
    left_to_model: tuple[LeftToModel, ...]
    issues: tuple[CheckIssue, ...]
    checks_applied: tuple[str, ...]
    checks_not_applied: tuple[tuple[str, str], ...]
    undeclared: tuple[tuple[int, str], ...]


def _judgment(entry: Sequence[Any]) -> RowJudgment | str:
    """The row-map entry as a `RowJudgment`, or the error text where it does not have the four
    fields (a model mistake: the row stays with the model). The two Literal fields are not checked
    here: the contract refuses a bad value row by row (`refused_by_contract`)."""
    try:
        return RowJudgment(*entry)
    except TypeError as error:
        return f"row-map entry is not (line_id, item_id, line_kind, sign_convention): {error}"


def _amount(value: Decimal | None) -> Decimal:
    return Decimal(0) if value is None else value


def _cell(row: ExtractedLine, column: int) -> Decimal:
    return _amount(row.values[column])


def _left(row: ExtractedLine, reason: str, detail: str) -> LeftToModel:
    return LeftToModel(row.line_no, row.locator, row.label, reason, detail)


def _body(
    judgment: RowJudgment,
    row: ExtractedLine,
    *,
    kind: Kind,
    period_id: str,
    priority: int,
    column: int,
    source_id: str,
    source_sha256: str,
    resolved: ResolvedLabel | None = None,
    quantity: StatementQuantity | None = None,
) -> dict[str, object]:
    cites = (
        tuple(
            {
                "source_id": source_id,
                "source_sha256": source_sha256,
                "locator": part.locator,
                "quote": part.text,
            }
            for part in resolved.parts
        )
        if resolved is not None
        else (
            {
                "source_id": source_id,
                "source_sha256": source_sha256,
                "locator": row.locator,
                "quote": row.label,
            },
        )
    )
    label = row.label if resolved is None else resolved.label
    return {
        "line_id": judgment.line_id,
        "statement": kind,
        "item_id": judgment.item_id,
        "label": label,
        "period_id": period_id,
        "display_priority": priority,
        "line_kind": judgment.line_kind,
        "value": {
            "observation_id": f"{judgment.line_id}.{period_id}",
            "status": "known",
            "amount": _cell(row, column),
            "citations": cites,
        },
        "sign_convention": judgment.sign_convention,
        "sign_citations": (cites[-1],) if judgment.sign_convention == "outflow_magnitude" else (),
        **({"quantity": quantity.model_dump(mode="python", exclude_none=True)} if quantity else {}),
        **(
            {"label_parts": tuple(part.model_dump(mode="python") for part in resolved.parts)}
            if resolved
            else {}
        ),
    }


def _row_lines(
    judgment: RowJudgment,
    row: ExtractedLine,
    columns: Sequence[str | None],
    *,
    kind: Kind,
    priority: int,
    source_id: str,
    source_sha256: str,
    resolved: ResolvedLabel | None = None,
    quantity: StatementQuantity | None = None,
) -> tuple[StatementLine, ...] | str:
    """The row's lines, or the contract's refusal text."""
    if kind == "BS" and judgment.sign_convention == "outflow_magnitude":
        return "balance-sheet amounts are signed balances, not outflow magnitudes"
    try:
        return tuple(
            StatementLine.model_validate(
                _body(
                    judgment,
                    row,
                    kind=kind,
                    period_id=period_id,
                    priority=priority,
                    column=column,
                    source_id=source_id,
                    source_sha256=source_sha256,
                    resolved=resolved,
                    quantity=quantity,
                )
            )
            for column, period_id in enumerate(columns)
            if period_id is not None
        )
    except ValidationError as error:
        first = error.errors()[0]
        return f"{'.'.join(str(part) for part in first['loc'])}: {first['msg']}"


def _identified(
    rows: Sequence[tuple[RowJudgment, ExtractedLine]], items: Collection[str]
) -> dict[str, list[ExtractedLine]]:
    found: dict[str, list[ExtractedLine]] = {item: [] for item in items}
    for judgment, row in rows:
        if judgment.item_id in found:
            found[judgment.item_id].append(row)
    return found


def _only(found: dict[str, list[ExtractedLine]], item: str) -> ExtractedLine | None:
    return found[item][0] if len(found[item]) == 1 else None


def _why_missing(found: dict[str, list[ExtractedLine]], items: Sequence[str]) -> str:
    absent = [item for item in items if not found[item]]
    repeated = [item for item in items if len(found[item]) > 1]
    parts = []
    if absent:
        parts.append(f"no composable row has item_id {', '.join(absent)}")
    if repeated:
        parts.append(f"item_id {', '.join(repeated)} names more than one row")
    return "; ".join(parts)


def _sums(
    columns: Sequence[str | None],
    left: Sequence[ExtractedLine],
    right: Sequence[ExtractedLine],
    check: str,
    text: str,
) -> list[CheckIssue]:
    issues = []
    for column, period_id in enumerate(columns):
        if period_id is None:
            continue
        lhs = sum((_cell(row, column) for row in left), Decimal(0))
        rhs = sum((_cell(row, column) for row in right), Decimal(0))
        if lhs != rhs:
            issues.append(
                CheckIssue(
                    check,
                    column,
                    period_id,
                    lhs,
                    rhs,
                    f"check {check} failed in column {column} ({period_id}): {text}: "
                    f"{lhs} != {rhs}",
                )
            )
    return issues


def _as_read(judgment: RowJudgment, row: ExtractedLine) -> ExtractedLine:
    """The row with each cell as the book reads it: -abs(cell) under `outflow_magnitude` (the
    prompts' sign rule and `financial_reconciliation`), unchanged when `signed`; a nil stays nil."""
    if judgment.sign_convention != "outflow_magnitude":
        return row
    values = tuple(None if v is None else v.copy_abs().copy_negate() for v in row.values)
    return replace(row, values=values)


def _checks(
    kind: Kind,
    rows: Sequence[tuple[RowJudgment, ExtractedLine]],
    columns: Sequence[str | None],
) -> tuple[list[CheckIssue], list[str], list[tuple[str, str]]]:
    """The failed checks, the checks applied and the checks not applied (with why)."""
    issues: list[CheckIssue] = []
    applied: list[str] = []
    skipped: list[tuple[str, str]] = []
    if kind == "BS":
        found = _identified(
            rows, (TOTAL_ASSETS, TOTAL_LIABILITIES, TOTAL_EQUITY, TOTAL_LIABILITIES_AND_EQUITY)
        )
        assets = _only(found, TOTAL_ASSETS)
        liabilities = _only(found, TOTAL_LIABILITIES)
        equity = _only(found, TOTAL_EQUITY)
        printed = _only(found, TOTAL_LIABILITIES_AND_EQUITY)
        if assets and liabilities and equity:
            applied.append(BS_LIABILITIES_PLUS_EQUITY)
            issues += _sums(
                columns,
                [assets],
                [liabilities, equity],
                BS_LIABILITIES_PLUS_EQUITY,
                "total assets != total liabilities + total equity",
            )
        else:
            skipped.append(
                (
                    BS_LIABILITIES_PLUS_EQUITY,
                    _why_missing(found, (TOTAL_ASSETS, TOTAL_LIABILITIES, TOTAL_EQUITY)),
                )
            )
        if assets and printed:
            applied.append(BS_PRINTED_TOTAL)
            issues += _sums(
                columns,
                [assets],
                [printed],
                BS_PRINTED_TOTAL,
                "total assets != total liabilities and equity",
            )
        else:
            both = (TOTAL_ASSETS, TOTAL_LIABILITIES_AND_EQUITY)
            skipped.append((BS_PRINTED_TOTAL, _why_missing(found, both)))
    elif kind == "CFS":
        rows = [(judgment, _as_read(judgment, row)) for judgment, row in rows]
        found = _identified(rows, (OPERATING, INVESTING, FINANCING, FX_EFFECT, NET_CHANGE))
        needed = (OPERATING, INVESTING, FINANCING, NET_CHANGE)
        parts = [_only(found, item) for item in needed]
        if len(found[FX_EFFECT]) > 1:
            skipped.append((CFS_NET_CHANGE, _why_missing(found, (FX_EFFECT,))))
        elif all(parts):
            sections = [row for row in parts[:3] if row]
            sections += found[FX_EFFECT]
            net = parts[3]
            applied.append(CFS_NET_CHANGE)
            issues += _sums(
                columns,
                sections,
                [net] if net else [],
                CFS_NET_CHANGE,
                "operating + investing + financing (+ FX) != net change",
            )
        else:
            skipped.append((CFS_NET_CHANGE, _why_missing(found, needed)))
    return issues, applied, skipped


_COMPARED = {
    BS_LIABILITIES_PLUS_EQUITY: (TOTAL_ASSETS, TOTAL_LIABILITIES, TOTAL_EQUITY),
    BS_PRINTED_TOTAL: (TOTAL_ASSETS, TOTAL_LIABILITIES_AND_EQUITY),
    CFS_NET_CHANGE: (OPERATING, INVESTING, FINANCING, FX_EFFECT, NET_CHANGE),
}


def _vacuous(
    applied: Sequence[str],
    rows: Sequence[tuple[RowJudgment, ExtractedLine]],
    columns: Sequence[str | None],
) -> bool:
    """True when an applied check compared only nil cells in a column it checked (0 == 0 proves
    nothing). An OCR unit does not count such a check as applied (R23.23, T22 fix 1)."""
    for check in applied:
        found = _identified(rows, _COMPARED[check])
        compared = [row for item in _COMPARED[check] for row in found[item]]
        for column, period_id in enumerate(columns):
            if period_id is not None and all(row.values[column] is None for row in compared):
                return True
    return False


def compose_unit(
    table: ExtractedTable,
    *,
    source_id: str,
    source_sha256: str,
    unit_locator: str,
    kind: Kind,
    column_periods: Sequence[str | None],
    row_map: Mapping[int, RowJudgment | tuple[str, str, str, str]],
    declared_periods: Collection[str],
    priority_offset: int = 0,
    other_rows: Mapping[int, str] = MappingProxyType({}),
    ocr: bool = False,
    note_page: bool = False,
    note_rows: Collection[int] = (),
    ocr_verified: bool = True,
    row_label_selections: Mapping[int, Sequence[int]] = MappingProxyType({}),
    row_dimensions: Mapping[int, StatementQuantity] = MappingProxyType({}),
    typed_profile: bool = False,
    book_currency: str = "",
    book_unit: str = "",
    context_tables: Sequence[ExtractedTable] | None = None,
) -> Composition:
    """Compose the statement lines of one extracted unit.

    `table` is the unit's extraction (`extract_statements` / `line_table`); `unit_locator` names
    it in the issue texts. `kind` is `BS`, `IS` or `CFS` (a comprehensive income unit is `IS`).
    `column_periods` is the model's column map: one period id or None per column, whose length
    is the unit's column count. `row_map` maps a row number (`ExtractedLine.line_no`) to its
    `RowJudgment`. `declared_periods` are the book's period ids. `priority_offset` is added to
    each row's position for `display_priority`. `other_rows` maps a row number to the statement
    its caption names when that is not `kind` (R23.22): such a row is not composed, whatever the
    row map holds, and is left with `OTHER_STATEMENT`. `ocr` says the unit's page was read by OCR
    (R23.23): its lines are written only if a check was applied and none failed or was skipped.
    `note_page` says the unit's page prints a note-reference column (R23.24): a row whose first
    value could be a note number is left with `NOTE_SUSPECT`, and so is a row whose number is in
    `note_rows` (the rows below a second header of the page).

    Returns the lines, the rows left to the model, the issues and which checks ran (module
    docstring). It raises nothing for a model's mistake; a mistake is returned as an issue, a
    left-to-model row or an `undeclared` column.
    """
    declared = frozenset(declared_periods)
    mapped = [p for p in column_periods if p is not None]
    if len(set(mapped)) != len(mapped):
        repeated = sorted({p for p in mapped if mapped.count(p) > 1})
        issue = CheckIssue(
            COLUMN_MAP_DISTINCT,
            column_periods.index(repeated[0]),
            repeated[0],
            None,
            None,
            f"unit {unit_locator}: the column map repeats {', '.join(repeated)}; nothing composed",
        )
        left_all = _all_left(table, UNIT_CHECK_FAILED, issue.message)
        return Composition((), left_all, (issue,), (), (), ())
    undeclared = tuple(
        (column, p)
        for column, p in enumerate(column_periods)
        if p is not None and p not in declared
    )
    columns = [p if p in declared else None for p in column_periods]
    left: list[LeftToModel] = []
    ready: list[tuple[int, RowJudgment, ExtractedLine]] = []
    counts = {row.line_no: 0 for row in table.lines}
    for row in table.lines:
        counts[row.line_no] += 1
    typed_resolutions: dict[int, ResolvedTypedRow] = {}
    for position, row in enumerate(table.lines, 1):
        if counts[row.line_no] > 1:
            left.append(_left(row, REPEATED_ROW, f"row number {row.line_no} is not unique"))
        elif set(row.flags) - {FOOTNOTE_MARKER}:
            left.append(_left(row, FLAGGED, ", ".join(row.flags)))
        elif len(row.values) != len(column_periods):
            left.append(
                _left(
                    row,
                    VALUE_COUNT,
                    f"{len(row.values)} values, the unit has {len(column_periods)} columns",
                )
            )
        elif row.line_no in other_rows:
            left.append(
                _left(
                    row,
                    OTHER_STATEMENT,
                    f"its caption names {other_rows[row.line_no]}, not this unit's {kind}; "
                    "Python writes no line for it and coverage does not require it",
                )
            )
        elif note_page and row.raw_values and _NOTE_LOOKING.fullmatch(row.raw_values[0]):
            left.append(_left(row, NOTE_SUSPECT, NOTE_SUSPECT_DETAIL))
        elif row.line_no in note_rows:
            left.append(_left(row, NOTE_SUSPECT, NOTE_BELOW_HEADER_DETAIL))
        elif row.line_no not in row_map:
            left.append(_left(row, NOT_IN_ROW_MAP, "no row-map entry"))
        elif isinstance(judgment := _judgment(row_map[row.line_no]), str):
            left.append(_left(row, BAD_ENTRY, judgment))
        elif typed_profile:
            if resolve_label_parts(table, row, row_label_selections.get(row.line_no, ())) is None:
                left.append(
                    _left(
                        row,
                        SOURCE_LABEL_REFUSED,
                        "the typed-source profile requires a source-bounded contiguous label selection",
                    )
                )
                continue
            resolution = _typed_row_resolution(
                table,
                row=row,
                source_id=source_id,
                source_sha256=source_sha256,
                row_label_selections=row_label_selections,
                row_dimensions=row_dimensions,
                book_currency=book_currency,
                book_unit=book_unit,
                context_tables=context_tables,
            )
            if resolution is None:
                left.append(
                    _left(
                        row,
                        SOURCE_QUANTITY_REFUSED,
                        "the typed-source profile requires current source unit evidence that agrees with the row label and book",
                    )
                )
                continue
            typed_resolutions[row.line_no] = resolution
            ready.append((position, judgment, row))
        else:
            ready.append((position, judgment, row))
    left += [
        LeftToModel(number, "", "", NO_SUCH_ROW, f"unit {unit_locator} has no row {number}")
        for number in sorted(set(row_map) - set(counts))
    ]
    issues, applied, skipped = _checks(kind, [(j, r) for _, j, r in ready], columns)
    if issues:
        left += [_left(row, UNIT_CHECK_FAILED, issues[0].message) for _, _, row in ready]
        return Composition(
            (), tuple(left), tuple(issues), tuple(applied), tuple(skipped), undeclared
        )
    lines: list[StatementLine] = []
    written: list[ExtractedLine] = []
    for position, judgment, row in ready:
        made = _row_lines(
            judgment,
            row,
            columns,
            kind=kind,
            priority=priority_offset + position,
            source_id=source_id,
            source_sha256=source_sha256,
            resolved=typed_resolutions[row.line_no].label if typed_profile else None,
            quantity=typed_resolutions[row.line_no].quantity if typed_profile else None,
        )
        if isinstance(made, str):
            left.append(_left(row, REFUSED, made))
        else:
            lines += made
            if made:
                written.append(row)
    if ocr and (
        not ocr_verified
        or not applied
        or skipped
        or _vacuous(applied, [(j, r) for _, j, r in ready], columns)
    ):
        left += [_left(row, OCR_UNCHECKED, OCR_UNCHECKED_DETAIL) for row in written]
        lines = []
    return Composition(tuple(lines), tuple(left), (), tuple(applied), tuple(skipped), undeclared)


def _all_left(table: ExtractedTable, reason: str, detail: str) -> tuple[LeftToModel, ...]:
    return tuple(_left(row, reason, detail) for row in table.lines)
