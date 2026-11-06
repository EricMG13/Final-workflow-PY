"""Unit maps: the model maps statement units, Python composes the lines (CP1H-R23, T21b).

The model-facing financials schema is `FinancialMapSubmission`: a `FinancialSubmission` plus
`unit_maps`, one `UnitMap` per located statement unit. A unit map names the unit (`source_id` and
`locator`), the book that owns it, the statement kind, the column map (one period id or null per
column, R23.1) and the four judgment fields of each row it maps. `expand` runs at the submit entry,
before the payload is bound, stored, filled or gated: it composes each map with
`statement_compose.compose_unit`, appends the lines to the named book's `statement_lines` and
drops `unit_maps`. From then on the composed `FinancialSubmission` JSON is the payload.

Python never picks a period or a book (R23.2). A unit composes nothing, and `Expansion.notes` says
why, when its map does not parse, names a book the payload does not have, names a unit not
extracted in this epoch, not a located statement unit (R23.27.3) or a source without a bindable
hash, repeats a row, repeats a unit, has a column map its own printed header does not verify
(R23.27.1), or fails a `compose_unit` check. Rows left to the model, check issues and undeclared columns are
notes too. Notes are for the model: they are not gate issues and are not journaled.

A payload that is not a JSON object, or has no `unit_maps` key, is returned byte-identical. A
`unit_maps` that is null or empty is dropped (the strict schema has the model send one when it
maps nothing; the contract refuses an unknown key). A `unit_maps` that is not a list is left in
place, with a note, for the core's shape error.
"""

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Literal

from pydantic import Field, ValidationError

from deploy_vii.contracts import Contract, Identifier
from deploy_vii.cp1_workflow import FinancialSubmission
from deploy_vii.financial_contracts import StatementQuantity
from deploy_vii.live.schema import exact_json, json_object
from deploy_vii.statement_extract import ExtractedTable
from deploy_workflow import statement_compose as sc

__all__ = [
    "Expansion",
    "FinancialMapSubmission",
    "RowDimension",
    "RowEntry",
    "RowLabelSelection",
    "UnitInputs",
    "UnitMap",
    "expand",
]

MAX_UNIT_NOTES = 12  # per unit: the check issues and undeclared columns come first
MAX_NOTES = 60  # in all; a last line counts the rest
MAX_NOTE_CHARS = 300


class RowEntry(Contract):
    """The four judgment fields of one row of a unit, by the row's number in the extraction."""

    row: int
    line_id: Identifier
    item_id: Identifier
    line_kind: Literal["detail", "subtotal", "total"]
    sign_convention: Literal["signed", "outflow_magnitude"]


class RowLabelSelection(Contract):
    """The selected contiguous physical source fragments for one extracted row."""

    row: int = Field(gt=0)
    part_line_numbers: tuple[int, ...] = Field(min_length=1)


class RowDimension(Contract):
    """The source-supported quantity kind and scale for one extracted row."""

    row: int = Field(gt=0)
    quantity: StatementQuantity


class UnitMap(Contract):
    """One located statement unit, mapped by the model."""

    source_id: Identifier
    locator: Identifier
    book_id: Identifier
    statement: Literal["BS", "IS", "CFS"]
    columns: tuple[Identifier | None, ...]
    rows: tuple[RowEntry, ...]
    profile: Literal["typed-source/1"] | None = None
    row_label_selections: tuple[RowLabelSelection, ...] = ()
    row_dimensions: tuple[RowDimension, ...] = ()


class FinancialMapSubmission(FinancialSubmission):
    """What the model submits for `financials`: the canonical submission plus its unit maps."""

    unit_maps: tuple[UnitMap, ...] = ()


HeaderColumns = Callable[[ExtractedTable, dict[str, Any]], tuple[frozenset[str], ...] | None]


def _no_header(table: ExtractedTable, book: dict[str, Any]) -> None:
    """The default `UnitInputs.ocr_header`: no header verifies any map (fail closed)."""


@dataclass(frozen=True)
class UnitInputs:
    """What the maps are composed against: the epoch's extracted tables (as the gate reads them)
    and the hash each ready source of the pack is bound to (what prefill fills a citation with)."""

    tables: Sequence[ExtractedTable]
    hashes: Mapping[str, str]
    other_rows: Mapping[tuple[str, str], Mapping[int, str]] = field(default_factory=dict)
    ocr_pages: frozenset[tuple[str, str]] = frozenset()  # (source_id, locator) read by OCR
    note_pages: frozenset[tuple[str, str]] = frozenset()  # (source_id, locator) with a Note column
    note_rows: Mapping[tuple[str, str], frozenset[int]] = field(default_factory=dict)
    # the period ids each column of a table's own header maps to in a payload book, or None; it
    # verifies the model's column map of every unit, text layer or OCR (R23.27.1)
    ocr_header: HeaderColumns = _no_header
    # the located statement units, (source_id, locator), OCR units included; a map of any other
    # range composes nothing (R23.27.3). Empty by default: a missing input never loosens the guard
    located: frozenset[tuple[str, str]] = frozenset()
    # Host-derived book dimensions are populated by authenticated financial prefill. Typed maps
    # cannot qualify themselves from hidden dimensions in their own submitted payload.
    book_dimensions: Mapping[str, tuple[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Expansion:
    """The payload to bind from here on, and the notes for the model."""

    payload: str
    notes: tuple[str, ...]


def _clip(text: str) -> str:
    return text if len(text) <= MAX_NOTE_CHARS else text[: MAX_NOTE_CHARS - 1] + "…"


def _bounded(notes: Sequence[str], limit: int) -> list[str]:
    """At most `limit` notes, clipped, then one line counting the rest."""
    shown = [_clip(note) for note in notes[:limit]]
    if len(notes) > limit:
        shown.append(f"and {len(notes) - limit} more notes")
    return shown


def _books(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    financial = document.get("financial")
    books = financial.get("books") if isinstance(financial, dict) else None
    if not isinstance(books, list):
        return {}
    return {
        book["book_id"]: book
        for book in books
        if isinstance(book, dict) and isinstance(book.get("book_id"), str)
    }


def _periods(book: dict[str, Any]) -> list[str]:
    periods = book.get("periods")
    if not isinstance(periods, list):
        return []
    return [
        p["period_id"]
        for p in periods
        if isinstance(p, dict) and isinstance(p.get("period_id"), str)
    ]


def _priority(lines: Sequence[Any]) -> int:
    """The highest `display_priority` among the lines (0 when none has an integer one)."""
    return max(
        (
            line["display_priority"]
            for line in lines
            if isinstance(line, dict) and type(line.get("display_priority")) is int
        ),
        default=0,
    )


def _typed_profile_problem(
    unit: UnitMap, book: Mapping[str, Any], table: ExtractedTable
) -> str | None:
    """Fail closed on incomplete typed rows or a period class that contradicts statement kind."""
    if unit.profile != "typed-source/1":
        return None
    row_numbers = {entry.row for entry in unit.rows}
    labels = [selection.row for selection in unit.row_label_selections]
    dimensions = [dimension.row for dimension in unit.row_dimensions]
    if len(labels) != len(set(labels)) or set(labels) != row_numbers:
        return "typed-source/1 requires exactly one label selection for every mapped row"
    if len(dimensions) != len(set(dimensions)) or set(dimensions) != row_numbers:
        return "typed-source/1 requires exactly one row dimension for every mapped row"
    periods = book.get("periods")
    if not isinstance(periods, list):
        return "typed-source/1 requires declared periods"
    by_id = {
        period.get("period_id"): period
        for period in periods
        if isinstance(period, dict) and isinstance(period.get("period_id"), str)
    }
    for period_id in unit.columns:
        if period_id is None:
            continue
        period = by_id.get(period_id)
        if period is None:
            return f"typed-source/1 column period {period_id} is not declared"
        if unit.statement == "BS":
            if period.get("period_type") != "PERIOD_END" or period.get("start_date") is not None:
                return (
                    "typed-source/1 balance-sheet columns require PERIOD_END periods with no "
                    "start date"
                )
        elif (
            period.get("period_type") == "PERIOD_END"
            or not period.get("start_date")
            or not period.get("end_date")
        ):
            return "typed-source/1 flow columns require supported duration periods with start and end dates"
    rows = {row.line_no: row for row in table.lines}
    for selection in unit.row_label_selections:
        row = rows.get(selection.row)
        if row is None or sc.resolve_label_parts(table, row, selection.part_line_numbers) is None:
            return f"typed-source/1 row {selection.row} has no valid bounded label selection"
    return None


def _dump(line: Any) -> dict[str, Any]:
    """A composed line as payload JSON: the amount a JSON number, not a string, as the model
    writes it; no nulls (every dropped field is a default)."""
    body: dict[str, Any] = line.model_dump(mode="json", exclude_none=True)
    body["value"]["amount"] = Decimal(format(line.value.amount, "f"))
    return body


def _left_note(where: str, item: sc.LeftToModel) -> str:
    if not item.locator:  # a row-map entry naming a row the unit does not have
        return f"{where}: {item.detail} ({item.reason})"
    return (
        f"{where}: row {item.line_no} {item.locator} ({item.label}) is left to you "
        f"({item.reason}): {item.detail}"
    )


def _unit_notes(where: str, result: sc.Composition) -> list[str]:
    notes = [f"{where}: {issue.message}" for issue in result.issues]
    notes += [
        f"{where}: column {column} maps {period_id}, which the book does not declare; "
        "no line is written for it"
        for column, period_id in result.undeclared
    ]
    notes += [_left_note(where, item) for item in result.left_to_model]
    return _bounded(notes, MAX_UNIT_NOTES)


def _entry(index: int, raw: Any) -> tuple[UnitMap | None, str]:
    """The parsed map, or None and the reason it does not parse."""
    try:
        return UnitMap.model_validate_json(exact_json(raw)), ""
    except ValidationError as error:
        first = error.errors()[0]
        place = ".".join(str(part) for part in first["loc"])
        return None, f"unit_maps[{index}] is malformed ({place}: {first['msg']}); nothing composed"


def _needs_quantity_hash(raw: Any) -> bool:
    """Whether a raw row-dimension citation omitted the hidden source hash field."""
    dimensions = raw.get("row_dimensions") if isinstance(raw, Mapping) else None
    if not isinstance(dimensions, list):
        return False
    return any(
        isinstance(dimension, Mapping)
        and isinstance((quantity := dimension.get("quantity")), Mapping)
        and isinstance((citations := quantity.get("citations")), list)
        and any(
            isinstance(citation, Mapping) and "source_sha256" not in citation
            for citation in citations
        )
        for dimension in dimensions
    )


def _bind_quantity_hash(raw: Any, source_sha256: str) -> Any:
    """Fill only absent model-hidden hashes on row dimensions; preserve any supplied value."""
    if not isinstance(raw, Mapping):
        return raw
    bound = dict(raw)
    dimensions = raw.get("row_dimensions")
    if not isinstance(dimensions, list):
        return raw
    bound_dimensions: list[Any] = []
    for dimension in dimensions:
        if not isinstance(dimension, Mapping):
            bound_dimensions.append(dimension)
            continue
        bound_dimension = dict(dimension)
        quantity = dimension.get("quantity")
        if isinstance(quantity, Mapping):
            bound_quantity = dict(quantity)
            citations = quantity.get("citations")
            if isinstance(citations, list):
                bound_quantity["citations"] = [
                    {**citation, "source_sha256": source_sha256}
                    if isinstance(citation, Mapping) and "source_sha256" not in citation
                    else citation
                    for citation in citations
                ]
            bound_dimension["quantity"] = bound_quantity
        bound_dimensions.append(bound_dimension)
    bound["row_dimensions"] = bound_dimensions
    return bound


def _header_verifies(
    mapped: tuple[frozenset[str], ...] | None, columns: Sequence[str | None]
) -> bool:
    """The unit's own printed header maps every column the model maps (R23.23.2): the mapped
    columns exist, have the model's length, and each non-null model period is in its column's
    mapped set."""
    return (
        mapped is not None
        and len(mapped) == len(columns)
        and all(p is None or p in ids for p, ids in zip(columns, mapped, strict=True))
    )


def _first_mismatch(
    mapped: tuple[frozenset[str], ...] | None, columns: Sequence[str | None]
) -> str:
    """Why `_header_verifies` is false: the first failing column, the model's period for it and
    the header's mapped ids for it (or "no header period")."""
    if mapped is None:
        first = next((i for i, p in enumerate(columns) if p is not None), 0)
        period = columns[first] if columns else None
        return f"column {first} maps {period}, but the unit's header gives no header period"
    if len(mapped) != len(columns):
        return (
            f"the map has {len(columns)} columns but the unit's header has {len(mapped)}; "
            f"column {min(len(mapped), len(columns))} has no counterpart"
        )
    index = next(
        i
        for i, (period, ids) in enumerate(zip(columns, mapped, strict=True))
        if period is not None and period not in ids
    )
    ids = mapped[index]
    given = ", ".join(sorted(ids)) if ids else "no header period"
    return f"column {index} maps {columns[index]}, but the unit's header gives {given}"


def _compose(
    index: int,
    unit: UnitMap,
    book: dict[str, Any],
    table: ExtractedTable,
    sha256: str,
    other_rows: Mapping[int, str] = MappingProxyType({}),
    ocr: bool = False,
    note_page: bool = False,
    note_rows: frozenset[int] = frozenset(),
    ocr_header: HeaderColumns = _no_header,
    book_dimensions: Mapping[str, tuple[str, str]] = MappingProxyType({}),
) -> tuple[list[dict[str, Any]], list[str]]:
    """The unit's composed lines (as payload JSON) and its notes. The caller has checked that the
    book, the unit and the source are known."""
    where = f"unit_maps[{index}] {unit.source_id} {unit.locator}"
    if problem := _typed_profile_problem(unit, book, table):
        return [], [f"{where}: {problem}; nothing composed"]
    dimensions = book_dimensions.get(unit.book_id)
    if unit.profile == "typed-source/1" and dimensions is None:
        return [], [f"{where}: authenticated book dimensions are unavailable; nothing composed"]
    numbers = [entry.row for entry in unit.rows]
    if len(set(numbers)) != len(numbers):
        repeated = sorted({n for n in numbers if numbers.count(n) > 1})
        return [], [f"{where}: rows {repeated} are mapped more than once; nothing composed"]
    lines = book.get("statement_lines")
    # ponytail: ceiling: a unit whose own printed header maps no column composes nothing, text
    # layer or OCR (a PDF unit until CP1H-R24; an OCR'd page whose header the OCR loses); upgrade:
    # read the period from the page title when the header is lost.
    mapped = ocr_header(table, book)
    verified = _header_verifies(mapped, unit.columns)
    if not verified and not ocr:
        why = _first_mismatch(mapped, unit.columns)
        return [], [f"{where}: {why}; nothing composed"]
    result = sc.compose_unit(
        table,
        source_id=unit.source_id,
        source_sha256=sha256,
        unit_locator=unit.locator,
        kind=unit.statement,
        column_periods=unit.columns,
        row_map={
            entry.row: sc.RowJudgment(
                entry.line_id, entry.item_id, entry.line_kind, entry.sign_convention
            )
            for entry in unit.rows
        },
        declared_periods=_periods(book),
        priority_offset=_priority(lines if isinstance(lines, list) else []),
        other_rows=other_rows,
        ocr=ocr,
        note_page=note_page,
        note_rows=note_rows,
        ocr_verified=verified,
        row_label_selections={
            selection.row: selection.part_line_numbers for selection in unit.row_label_selections
        },
        row_dimensions={dimension.row: dimension.quantity for dimension in unit.row_dimensions},
        typed_profile=unit.profile == "typed-source/1",
        book_currency=(dimensions[0] if dimensions is not None else str(book.get("currency", ""))),
        book_unit=(dimensions[1] if dimensions is not None else str(book.get("unit", ""))),
    )
    return [_dump(line) for line in result.lines], _unit_notes(where, result)


def expand(
    payload: str, *, extracted: Collection[tuple[str, str]], inputs: Callable[[], UnitInputs]
) -> Expansion:
    """Compose the payload's unit maps (module docstring). `extracted` is the epoch's
    `(source_id, locator)` units; `inputs` is called at most once, and only when a map has to be
    composed."""
    document = json_object(payload)
    if document is None or "unit_maps" not in document:
        return Expansion(payload, ())
    raw = document["unit_maps"]
    if raw is None or raw == []:
        del document["unit_maps"]
        return Expansion(exact_json(document), ())
    if not isinstance(raw, list):
        return Expansion(payload, ("unit_maps is not a list; nothing composed",))
    books = _books(document)
    notes: list[str] = []
    composed: set[tuple[str, str, str]] = set()
    available: UnitInputs | None = None
    for index, item in enumerate(raw):
        unit, problem = _entry(index, item)
        if unit is None and _needs_quantity_hash(item):
            raw_source_id = item.get("source_id") if isinstance(item, Mapping) else None
            if isinstance(raw_source_id, str):
                available = available or inputs()
                if digest := available.hashes.get(raw_source_id):
                    unit, problem = _entry(index, _bind_quantity_hash(item, digest))
        if unit is None:
            notes.append(problem)
            continue
        where = f"unit_maps[{index}] {unit.source_id} {unit.locator}"
        key = (unit.source_id, unit.locator)
        book = books.get(unit.book_id)
        if book is None:
            notes.append(f"{where}: the payload has no book {unit.book_id}; nothing composed")
            continue
        if key not in extracted:
            notes.append(f"{where}: this unit was not extracted in this epoch; nothing composed")
            continue
        held = book.get("statement_lines")
        if held is not None and not isinstance(held, list):
            notes.append(f"{where}: the book's statement_lines is not a list; nothing composed")
            continue
        if (*key, unit.book_id) in composed:
            notes.append(f"{where}: the unit is mapped more than once; nothing composed")
            continue
        available = available or inputs()
        if key not in available.located:
            notes.append(f"{where}: not a located statement unit; nothing composed")
            continue
        table = next(
            (t for t in available.tables if (t.source_id, t.locator) == key),
            None,
        )
        sha256 = available.hashes.get(unit.source_id)
        if table is None or sha256 is None:
            what = "no extracted table" if table is None else "no bindable source hash"
            notes.append(f"{where}: {what} for the unit; nothing composed")
            continue
        lines, unit_notes = _compose(
            index,
            unit,
            book,
            table,
            sha256,
            available.other_rows.get(key, {}),
            ocr=key in available.ocr_pages,
            note_page=key in available.note_pages,
            note_rows=available.note_rows.get(key, frozenset()),
            ocr_header=available.ocr_header,
            book_dimensions=available.book_dimensions,
        )
        notes += unit_notes
        if lines:
            composed.add((*key, unit.book_id))
            held = book.get("statement_lines")
            book["statement_lines"] = [*(held if isinstance(held, list) else []), *lines]
    del document["unit_maps"]
    return Expansion(exact_json(document), tuple(_bounded(notes, MAX_NOTES)))
