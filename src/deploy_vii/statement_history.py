"""Full statement-line period construction using the reviewed historical kernel.

No Model readiness gate: incomplete add-back disclosure does not stop statement
arithmetic. Reported figures remain in the source artifact and never plug a
missing derived component. Every calculation retains its actual operand graph.
"""

from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal, localcontext
from typing import Literal

from deploy_vii.calculation_trace import Computation, trace_cells
from deploy_vii.contracts import Citation, Contract, Identifier, Text
from deploy_vii.financial_adapter import _periods
from deploy_vii.financial_contracts import (
    FinancialPeriod,
    FinancialReview,
    StatementQuantityKind,
    Unit,
)
from deploy_vii.financial_periods import (
    PeriodConstruction,
    PeriodReference,
    PeriodValue,
    _constructions,
    _id,
    _reference,
)
from deploy_vii.model import history
from deploy_vii.model._cells import CONTEXT, SIGN_NORMALISED, join_notes, opening_date
from deploy_vii.model.frame import Cell, SourceRef
from deploy_vii.model.periods import _period_spec, _plan, _Spec
from deploy_vii.model.registers import Cp1Registers
from deploy_vii.preparation import PreparedPack
from deploy_vii.statement_output import StatementCell, StatementReport, statement_report


class StatementPeriodOperand(Contract):
    reference: PeriodReference
    computation_id: Identifier


class StatementHistoricalValue(Contract):
    value_id: Identifier
    construction_id: Identifier
    table_id: Literal["T4.4", "T4.5", "T4.6"]
    item_id: Identifier
    quantity_kind: Literal["monetary", "currency_per_share", "shares"]
    quantity_unit: Text
    currency: Text | None
    scale: Unit
    factor: Decimal
    quantity_citations: tuple[Citation, ...]
    value: PeriodValue
    computation_id: Identifier
    operands: tuple[StatementPeriodOperand, ...]
    stated_computation_id: Identifier | None


class StatementHistoryReport(Contract):
    schema_version: Literal["statement-history/2"] = "statement-history/2"
    source: StatementReport
    periods: tuple[FinancialPeriod, ...]
    columns: tuple[Identifier, ...]
    constructions: tuple[PeriodConstruction, ...]
    values: tuple[StatementHistoricalValue, ...]
    computations: tuple[Computation, ...]


def _input(cell: StatementCell) -> Cell:
    source = (
        (SourceRef(cell.observation_id, "financial-observation", str(cell.source_amount)),)
        if cell.observation_id
        else ()
    )
    if cell.normalized_amount is None:
        return Cell(
            None,
            "NOT_APPLICABLE" if cell.status == "not_applicable" else "NOT_STATED",
            input_sources=source,
            note=cell.limitation,
        )
    return Cell(
        cell.normalized_amount,
        basis="REPORTED",
        sources=source,
        note=SIGN_NORMALISED if cell.value_class == "normalized" else None,
    )


def _select(available: list[StatementCell]) -> Cell:
    """The first figure among same-date observations; a conflict or disagreeing figures
    block selection."""
    amounts = {cell.normalized_amount for cell in available if cell.normalized_amount is not None}
    if len(amounts) > 1 or any(cell.status == "conflicting" for cell in available):
        return Cell(
            None,
            "COMPONENT_MISSING",
            note="Unresolved conflicting statement observations at the balance date",
            input_sources=tuple(
                ref
                for cell in available
                for ref in (_input(cell).sources or _input(cell).input_sources)
            ),
        )
    selected = next((cell for cell in available if cell.normalized_amount is not None), None)
    if selected is None:
        selected = next((cell for cell in available if cell.observation_id), None)
    return _input(selected) if selected else Cell(None, "NOT_SOURCED")


def _at(
    cells: dict[str, StatementCell], period_ids: tuple[str, ...], own: str | None
) -> list[StatementCell]:
    """The item's observations for these periods, the column's own period first."""
    ordered = tuple(dict.fromkeys((own, *period_ids)))
    return [cells[pid] for pid in ordered if pid in period_ids and pid in cells]


def _closing(
    cells: dict[str, StatementCell], periods: tuple[FinancialPeriod, ...], spec: _Spec
) -> Cell:
    """Closing observations only; an unresolved same-date conflict blocks selection."""
    end = spec.column.end_date
    if end is None:
        return Cell(None, "NOT_SOURCED", note="Closing date is unavailable")
    matching = tuple(p.period_id for p in periods if p.end_date and p.end_date.isoformat() == end)
    return _select(_at(cells, matching, spec.own))


def _opening(
    cells: dict[str, StatementCell],
    closing: dict[str, StatementCell],
    periods: tuple[FinancialPeriod, ...],
    spec: _Spec,
) -> Cell:
    """CFS cash at the day before the column starts: an opening-cash observation of
    a period starting with the column, else the CFS closing cash of a period ending
    the day before; an unresolved conflict at that date blocks selection."""
    opening = opening_date(spec.column)
    if opening is None:
        return Cell(None, "NOT_SOURCED", note="Opening date is unavailable")
    starting = tuple(
        p.period_id
        for p in periods
        if p.start_date and (p.start_date - timedelta(days=1)).isoformat() == opening
    )
    ending = tuple(p.period_id for p in periods if p.end_date and p.end_date.isoformat() == opening)
    own = _at(cells, starting, spec.own)
    cell = _select([*own, *_at(closing, ending, None)])
    if cell.value is None or any(c.normalized_amount is not None for c in own):
        return cell
    return replace(cell, note=join_notes(cell.note, f"CFS closing cash at {opening}"))


def _derived_specs(regs: Cp1Registers) -> tuple[_Spec, ...]:
    planned = list(_plan(regs))
    seen: set[str] = set()
    derived: list[_Spec] = []

    def visit(spec: _Spec) -> None:
        if spec.column.column_id in seen:
            return
        seen.add(spec.column.column_id)
        if spec.terms is not None:
            derived.append(spec)
        for ref, _ in spec.terms or ():
            if isinstance(ref, _Spec):
                visit(ref)

    # Check ambiguous kernel identities before deduplicating the traversal.
    _constructions(tuple(planned))
    for spec in planned:
        visit(spec)
    for period in regs.periods:
        if (
            period.period_type in {"YTD", "FY"}
            and period.component_period_ids
            and not any(spec.own == period.period_id for spec in derived)
        ):
            visit(_period_spec(period, "FY" if period.period_type == "FY" else "YTD"))
    return tuple(derived)


def _component_period_ids(spec: _Spec) -> tuple[str, ...]:
    """Return the actual source periods under a construction without doing its arithmetic."""
    result: list[str] = []

    def visit(reference: str | PeriodReference | _Spec | None) -> None:
        if isinstance(reference, _Spec):
            if reference.terms is None:
                if reference.own is not None:
                    result.append(reference.own)
            else:
                for child, _ in reference.terms:
                    visit(child)
        elif isinstance(reference, PeriodReference):
            if reference.kind == "period" and reference.reference is not None:
                result.append(reference.reference)
        elif reference is not None:
            result.append(reference)

    for reference, _ in spec.terms or ():
        visit(reference)
    return tuple(dict.fromkeys(result))


def _lineage(computations: tuple[Computation, ...]) -> dict[str, PeriodValue]:
    """Include missing operands' evidence, which a null arithmetic root cannot carry."""
    result: dict[str, PeriodValue] = {}
    for node in computations:  # trace_cells emits children before their parent.
        values = (node.value, *(result[o.computation_id] for o in node.operands))
        result[node.computation_id] = node.value.model_copy(
            update={
                "observation_ids": tuple(
                    dict.fromkeys(i for v in values for i in v.observation_ids)
                ),
                "citations": tuple(dict.fromkeys(c for v in values for c in v.citations)),
            }
        )
    return result


_Table = Literal["T4.4", "T4.5", "T4.6"]
_Key = tuple[_Table, str]
_Dimensions = tuple[StatementQuantityKind, Text, Text | None, Unit, Decimal]
_NONMONETARY_UNBUILT = (
    "Nonmonetary statement values are report-only; no direct "
    "observation exists for this exact source period, so no "
    "period arithmetic is applied"
)


@dataclass(frozen=True, slots=True)
class _Item:
    key: _Key
    dimensions: _Dimensions
    cells: dict[str, StatementCell]
    series: history._Series


def _dimensions(key: _Key, cells: dict[str, StatementCell]) -> _Dimensions | None:
    dimensions = {
        (cell.quantity_kind, cell.quantity_unit, cell.currency, cell.scale, cell.factor)
        for cell in cells.values()
    }
    if len(dimensions) > 1:
        raise ValueError(f"Statement dimensions vary across periods for {key[0]}/{key[1]}")
    return next(iter(dimensions), None)


def _balance(
    key: _Key,
    cells_by_item: dict[_Key, dict[str, StatementCell]],
    periods: tuple[FinancialPeriod, ...],
    spec: _Spec,
) -> Cell | None:
    """A balance read at a date (BS items and CFS cash); None for a flow. A balance is
    never built by period arithmetic."""
    cells = cells_by_item[key]
    if key[0] == "T4.6" or key == ("T4.5", "closing_cash"):
        return _closing(cells, periods, spec)
    if key == ("T4.5", "opening_cash"):
        return _opening(cells, cells_by_item.get(("T4.5", "closing_cash"), {}), periods, spec)
    return None


def _column_cells(
    item: _Item,
    cells_by_item: dict[_Key, dict[str, StatementCell]],
    periods: tuple[FinancialPeriod, ...],
    register: history._Register,
    spec: _Spec,
) -> tuple[Cell, tuple[tuple[PeriodReference, Cell], ...]]:
    """The column's cell and, for a flow built from periods, its term cells."""
    if item.dimensions[0] != "monetary":
        direct = item.cells.get(spec.own or "")
        if direct is None:
            return Cell(None, "COMPONENT_MISSING", note=_NONMONETARY_UNBUILT), ()
        return _input(direct), ()
    balance = _balance(item.key, cells_by_item, periods, spec)
    if balance is not None:
        return balance, ()
    flow = history._flow(item.series, register, spec)
    terms = tuple(
        (_reference(ref, sign), history._term(item.series, register, ref))
        for ref, sign in spec.terms or ()
    )
    return flow, terms


def _with_components(
    value: PeriodValue,
    ids: tuple[str, ...],
    cells: dict[str, StatementCell],
    component_ids: set[str],
) -> tuple[PeriodValue, tuple[str, ...]]:
    """A nonmonetary value without arithmetic keeps its component observations' evidence."""
    component_cells = tuple(cell for cell in cells.values() if cell.period_id in component_ids)
    ids = tuple(
        dict.fromkeys(
            (*ids, *(cell.observation_id for cell in component_cells if cell.observation_id))
        )
    )
    value = value.model_copy(
        update={
            "observation_ids": ids,
            "citations": tuple(
                dict.fromkeys(
                    (
                        *value.citations,
                        *(citation for cell in component_cells for citation in cell.citations),
                    )
                )
            ),
            "note": value.note
            or "Nonmonetary values are retained only as exact-period source observations",
        }
    )
    return value, ids


def _relevant_cells(
    cells: dict[str, StatementCell],
    ids: tuple[str, ...],
    own: str | None,
    component_ids: tuple[str, ...],
) -> tuple[StatementCell, ...]:
    """The item's observations a value used, or its own or component periods'."""
    periods = {*component_ids, *((own,) if own is not None else ())}
    return tuple(
        cell for cell in cells.values() if cell.observation_id in ids or cell.period_id in periods
    )


def statement_history(
    pack: PreparedPack, review: FinancialReview, book_id: str
) -> StatementHistoryReport:
    source = statement_report(pack, review, book_id)
    review = FinancialReview.model_validate_json(review.model_dump_json())
    book = next(b for b in review.books if b.book_id == book_id)
    regs = Cp1Registers(_periods(book), (), (), (), (), (), (), book.currency, book.unit)
    specs = _derived_specs(regs)
    constructions = _constructions(specs)
    register = history._register(regs)
    cells_by_item: dict[_Key, dict[str, StatementCell]] = {}
    for cell in source.cells:
        cells_by_item.setdefault((cell.table_id, cell.item_id), {})[cell.period_id] = cell
    specs_by_construction = {_id("period", spec.column.column_id): spec for spec in specs}
    component_ids_by_construction = {
        construction: _component_period_ids(spec)
        for construction, spec in specs_by_construction.items()
    }
    raw: dict[str, Cell] = {}
    operands: dict[str, tuple[tuple[PeriodReference, str], ...]] = {}
    comparisons: dict[str, str | None] = {}
    dimensions_by_identity: dict[str, _Dimensions] = {}
    identities: list[tuple[str, str, _Table, str]] = []
    with localcontext(CONTEXT):
        for key, cells in cells_by_item.items():
            dimensions = _dimensions(key, cells)
            if dimensions is None:
                continue
            series = history._Series("flow", {pid: _input(c) for pid, c in cells.items()})
            entry = _Item(key, dimensions, cells, series)
            for spec in specs:
                identity = _id("statement-history", *key, spec.column.column_id)
                identities.append((identity, _id("period", spec.column.column_id), *key))
                raw[identity], terms = _column_cells(
                    entry, cells_by_item, book.periods, register, spec
                )
                term_keys = tuple(f"{identity}:term:{i}" for i in range(len(terms)))
                raw.update(zip(term_keys, (term for _, term in terms), strict=True))
                operands[identity] = tuple(
                    zip((reference for reference, _ in terms), term_keys, strict=True)
                )
                stated = cells.get(spec.stated or "") if dimensions[0] == "monetary" else None
                comparisons[identity] = None if stated is None else identity + ":stated"
                if stated is not None:
                    raw[identity + ":stated"] = _input(stated)
                dimensions_by_identity[identity] = dimensions
    computations, roots = trace_cells(raw, book)
    lineage = _lineage(computations)
    conflicts = {c.observation_id for c in source.cells if c.status == "conflicting"}
    values = []
    for identity, construction, table, item in identities:
        value = lineage[roots[identity]]
        # An unspanned period still retains its attempted component evidence.
        evidence = (value, *(lineage[roots[key]] for _, key in operands[identity]))
        ids = tuple(dict.fromkeys(i for v in evidence for i in v.observation_ids))
        kind, quantity_unit, currency, scale, factor = dimensions_by_identity[identity]
        if kind != "monetary" and value.amount is None:
            value, ids = _with_components(
                value,
                ids,
                cells_by_item[(table, item)],
                set(component_ids_by_construction[construction]),
            )
        relevant_cells = _relevant_cells(
            cells_by_item[(table, item)],
            ids,
            specs_by_construction[construction].own,
            component_ids_by_construction[construction],
        )
        quantity_citations = tuple(
            dict.fromkeys(
                citation for cell in relevant_cells for citation in cell.quantity_citations
            )
        )
        if value.amount is None and conflicts.intersection(ids):
            value = value.model_copy(update={"calculation_status": "Conflicted"})
        value = value.model_copy(
            update={
                "observation_ids": ids,
                "citations": tuple(
                    dict.fromkeys(
                        (
                            *(c for v in evidence for c in v.citations),
                            *value.citations,
                            *(
                                citation
                                for cell in relevant_cells
                                for citation in cell.quantity_citations
                            ),
                        )
                    )
                ),
            }
        )
        comparison = comparisons[identity]
        values.append(
            StatementHistoricalValue(
                value_id=identity,
                construction_id=construction,
                table_id=table,
                item_id=item,
                quantity_kind=kind,
                quantity_unit=quantity_unit,
                currency=currency,
                scale=scale,
                factor=factor,
                quantity_citations=quantity_citations,
                value=value,
                computation_id=roots[identity],
                operands=tuple(
                    StatementPeriodOperand(reference=ref, computation_id=roots[key])
                    for ref, key in operands[identity]
                ),
                stated_computation_id=roots[comparison] if comparison else None,
            )
        )
    return StatementHistoryReport(
        source=source,
        periods=book.periods,
        columns=tuple(_id("period", spec.column.column_id) for spec in specs),
        constructions=constructions,
        values=tuple(values),
        computations=computations,
    )


def validate_statement_history(
    pack: PreparedPack, review: FinancialReview, report: StatementHistoryReport
) -> tuple[str, ...]:
    try:
        report = StatementHistoryReport.model_validate_json(report.model_dump_json())
        expected = statement_history(pack, review, report.source.book_id)
    except ValueError as error:
        return (f"Invalid statement history: {error}",)
    return (
        ()
        if report.content_hash() == expected.content_hash()
        else ("Statement history differs from trusted recomputation",)
    )
