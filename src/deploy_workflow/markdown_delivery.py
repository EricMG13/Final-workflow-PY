"""Literal Markdown-to-report adapter, separate from native analytical contracts.

Existing report/index/table/prose components own presentation. This adapter
retains the actual handoffs, text and source lines; it performs no financial
calculation, journal promotion or analytical execution.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Context, Decimal
from pathlib import Path

from deploy_vii.bindings import Binding, BindingMap, validate_bindings
from deploy_vii.contracts import (
    Citation,
    Fact,
    ModuleView,
    ReportTable,
    Run,
    Source,
    TableColumn,
    TableRow,
    View,
)
from deploy_vii.display import UnitClass
from deploy_vii.registry import modules
from deploy_vii.render import render
from deploy_vii.report_view import (
    Block,
    BlockTab,
    CallItem,
    FactCoord,
    Pathway,
    ReportView,
    _call,
    _ChartPoint,
    _figure_of_points,
    _prose_lines,
    _refs_by_fact,
    _slot,
    _spec_of,
    _unplaced,
    build_index,
    pathways,
)
from deploy_workflow.handoff_delivery import (
    EXACT_NUMBER,
    DeliveryRequest,
    FigureId,
    MarkdownLayout,
    MarkdownRoute,
    exact_number,
    fence_blocks,
    heading_text,
    names_issuer,
    plain,
    section,
    token_decimals,
    with_scope_banner,
)

CHART_UNITS: dict[str, UnitClass] = {"x": "multiple", "US$m": "amount", "%": "percent"}
# Chart unit -> the typed unit, scale and currency of its observations.
CHART_TYPES: dict[str, tuple[str, Decimal, str | None]] = {
    "x": ("MULTIPLE", Decimal(1), None),
    "US$m": ("MILLIONS", Decimal(1000000), "USD"),
    "%": ("PERCENT", Decimal(1), None),
}
# A source column that states each row's own unit; it outranks the route's chart unit.
REPORTING_UNIT = "Reporting unit"
SHARE_QUANTITY = re.compile(r"per\s+share|USD\s*/\s*share|million.*shares", re.IGNORECASE)
GAP_TOKENS = frozenset({"—", "Insufficient Information", "Not reconstructed"})

STRIP_FIGURES: dict[str, tuple[FigureId, ...]] = {
    "model-chart-strip": ("S.1", "S.2", "S.3", "S.4"),
    "metric-strip": ("S.1", "S.2", "S.3"),
    "maturity-wall": ("S.4",),
    "yield-against-maturity": ("RV.1",),
}
STRIP_SUMMARY = (
    "Exact selected handoff/Model observations. Dates, definitions and limitations remain in the "
    "source evidence; gaps are not zero."
)
YIELD_SUMMARY = (
    "Separate clean/dirty assumptions; categorical note maturities, not an observed or fitted "
    "curve. Raw values remain in the source table; labels use at most six decimal places."
)
LITERAL_LIMITATION = (
    "Literal checked analytical handoff, not native contract acceptance; source qualifications "
    "and gaps remain."
)

Paragraph = list[tuple[int, str]]


def _paragraphs(lines: list[str]) -> dict[tuple[str, ...], list[Paragraph]]:
    """Wrapped paragraphs keyed by their heading path, so equal titles in different sections stay
    apart. A fenced code block is one literal paragraph; nothing in it is a heading or table."""
    blocks = fence_blocks(lines)
    paragraphs: dict[tuple[str, ...], list[Paragraph]] = {}
    path: list[tuple[int, str]] = []
    pending: Paragraph = []
    previous = 0
    for number, line in enumerate([*lines, ""], 1):
        block = blocks[number - 1] if number <= len(lines) else 0
        title = None if block else heading_text(line)
        if block:
            content, boundary = bool(line.strip()), block != previous
        else:
            content = bool(line.strip()) and title is None and not line.startswith(("|", "<!--"))
            boundary = not content or previous != 0
        if boundary and pending:
            paragraphs.setdefault(tuple(t for _, t in path) or ("Document",), []).append(pending)
            pending = []
        previous = block
        if title is not None:
            level = len(line) - len(line.lstrip("#"))
            while path and path[-1][0] >= level:
                path.pop()
            path.append((level, title))
        elif content:
            pending.append((number, line))
    return paragraphs


def _paragraph_text(paragraph: Paragraph) -> str:
    """Wrapped lines joined; inline emphasis is removed except in fenced code, kept verbatim."""
    text = " ".join(line.strip() for _, line in paragraph)
    return text if paragraph[0][1].lstrip().startswith(("```", "~~~")) else plain(text)


def _prose_table(
    module_id: str, digest: str, table_id: str, heading: str, groups: list[Paragraph]
) -> tuple[list[Fact], ReportTable]:
    facts = []
    rows = []
    for number, paragraph in enumerate(groups):
        fact_id = f"{table_id}.r{number}.c0"
        facts.append(
            Fact(
                fact_id=fact_id,
                label=heading,
                table_id=table_id,
                row_id=f"r{number}",
                field="c0",
                text=_paragraph_text(paragraph),
                value_class="source",
                basis="Literal wrapped paragraph from the model-authored handoff; no new analysis.",
                citations=tuple(
                    Citation(
                        source_id=module_id,
                        source_sha256=digest,
                        locator=f"line {n}",
                        quote=line,
                    )
                    for n, line in paragraph
                ),
            )
        )
        rows.append(
            TableRow(
                row_id=f"r{number}",
                label=f"{heading} — paragraph {number + 1}",
                fact_ids=(fact_id,),
            )
        )
    table = ReportTable(
        table_id=table_id,
        title=heading,
        row_header="Paragraph",
        columns=(TableColumn(field="c0", label="Text"),),
        rows=tuple(rows),
    )
    return facts, table


def literal_module(
    module_id: str, raw: bytes
) -> tuple[ModuleView, Source, dict[str, tuple[str, str]]]:
    """Retain tables and wrapped prose with exact physical-line citations."""
    from deploy_workflow.model_handoff_delivery import _literal_tables

    descriptor = next((m for m in modules() if m.module_id == module_id), None)
    if descriptor is None:
        raise ValueError(f"markdown_module: unknown module {module_id}")
    digest = hashlib.sha256(raw).hexdigest()
    source, facts, tables, _ = _literal_tables(module_id, raw, digest)
    lines = raw.decode("utf-8").splitlines()
    blocks = fence_blocks(lines)
    headings = [
        (n, title)
        for n, line in enumerate(lines, 1)
        if not blocks[n - 1] and (title := heading_text(line)) is not None
    ]
    metadata: dict[str, tuple[str, str]] = {}
    fact_map = {f.fact_id: f for f in facts}
    for i, table in enumerate(tables):
        first = fact_map[table.rows[0].fact_ids[0]].citations[0]
        number = int(first.locator.split()[-1])
        heading = next((title for n, title in reversed(headings) if n < number), "Document")
        tables[i] = table.model_copy(
            update={"title": heading + " — " + (table.row_header or "Table")}
        )
        metadata[table.table_id] = (heading, "table")
    for index, (path, groups) in enumerate(_paragraphs(lines).items()):
        table_id = f"prose-{module_id}-{index}"
        prose_facts, prose = _prose_table(module_id, digest, table_id, path[-1], groups)
        facts.extend(prose_facts)
        tables.append(prose)
        metadata[table_id] = (path[-1], "prose")
    return (
        ModuleView(
            module_id=module_id,
            title=descriptor.title,
            aliases=descriptor.aliases,
            status="candidate",
            artifact_sha256=digest,
            facts=tuple(facts),
            tables=tuple(tables),
            limitations=(LITERAL_LIMITATION,),
        ),
        source,
        metadata,
    )


def _portfolio_call(
    module: ModuleView | None,
    metadata: dict[str, tuple[str, str]],
    refs: dict[tuple[str, str], tuple[str, ...]],
    *,
    portfolio: bool = True,
) -> CallItem | None:
    """Copy CP-6's explicit terminal posture; never infer a decision or confidence."""
    if module is None or module.module_id != "CP-6":
        return None
    heading = "Final Sizing Posture" if portfolio else "Action Bias Determination"
    prefix = "Final Sizing Posture:" if portfolio else "Final Action Bias:"
    choices = (
        r"Include|Avoid|Resize-Reduce|Resize-Increase|Maintain-Hold|Requires More Work"
        if portfolio
        else r"Avoid|Watchlist|Starter Position|Core Hold|Add / Increase|Reduce / Trim|Exit"
        r"|Requires More Work"
    )
    records = [
        fact
        for fact in module.facts
        if metadata.get(fact.table_id) == (heading, "prose")
        and (fact.text or "").startswith(prefix)
    ]
    if not records:
        return None
    match = re.match(
        re.escape(prefix) + " (" + choices + r")(?:\.(?:\s|$)|$)",
        records[0].text or "",
    )
    source_ref = next(
        (
            ref
            for ref in refs.get((module.module_id, records[0].fact_id), ())
            if ref.startswith("C")
        ),
        None,
    )
    if len(records) != 1 or match is None or source_ref is None:
        raise ValueError(
            "markdown_posture: one explicit terminal CP-6 posture with a citation required"
        )
    return CallItem(
        kind="fact",
        label="Portfolio posture" if portfolio else "Action bias",
        value_text=match[1],
        ref_id=source_ref,
    )


def _yield_observations(
    module: ModuleView, table: ReportTable, as_of: date
) -> tuple[ModuleView, tuple[str, ...], tuple[_ChartPoint, ...]]:
    """Type explicit yield cells for the existing figure; retain the literal table unchanged."""
    if (
        module.module_id not in {"CP-3", "CP-3D"}
        or table.row_header != "Instrument"
        or tuple(c.label for c in table.columns) != ("Maturity", "Price basis", "Yield, %")
    ):
        raise ValueError("markdown_yield: expected Instrument / Maturity / Price basis / Yield, %")
    facts = {f.fact_id: f for f in module.facts}
    tid = "chart-" + table.table_id
    values, rows, points = [], [], []
    seen = set()
    maturities: dict[str, str] = {}
    for index, row in enumerate(table.rows):
        maturity, basis, source = (facts[fid] for fid in row.fact_ids)
        if (
            maturity.status != "known"
            or maturity.text is None
            or date.fromisoformat(maturity.text).isoformat() != maturity.text
            or date.fromisoformat(maturity.text) <= as_of
            or basis.text not in {"Assume clean", "Assume dirty"}
        ):
            raise ValueError(
                "markdown_yield: future ISO maturity and explicit price assumption required"
            )
        if maturities.setdefault(row.label, maturity.text) != maturity.text:
            raise ValueError("markdown_yield: conflicting maturities for one instrument")
        key = (row.label, basis.text)
        if key in seen:
            raise ValueError(
                "markdown_yield: duplicate instrument/maturity/price-basis observation"
            )
        seen.add(key)
        amount = None
        decimals = None
        if source.status == "known":
            token = source.text or ""
            if len(token) > 64 or re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", token) is None:
                raise ValueError(
                    "markdown_yield: yield must be a finite plain percentage-point token"
                )
            value = Decimal(token)
            # Decimal construction is exact; this is unit representation, not a yield calculation.
            amount = value.scaleb(-2, context=Context(prec=max(28, len(value.as_tuple().digits))))
            decimals = min(6, len(token.partition(".")[2]))
        fact_id = f"{tid}.r{index}.value"
        values.append(
            Fact(
                fact_id=fact_id,
                table_id=tid,
                row_id=f"r{index}",
                field="value",
                label=row.label,
                amount=amount,
                status=source.status,
                unit="PERCENT",
                period=as_of.isoformat(),
                decimals=decimals,
                citations=source.citations,
                limitation=source.limitation,
                basis="Conditional model yield copied from Markdown; percentage points / 100 for "
                "display, no repricing.",
                value_class="source",
            )
        )
        category = f"{maturity.text} · {row.label}"
        rows.append(
            TableRow(row_id=f"r{index}", label=f"{category} · {basis.text}", fact_ids=(fact_id,))
        )
        points.append(_ChartPoint(series=basis.text, category=category, fact_id=fact_id))
    if len(seen) != 2 * len(maturities):
        raise ValueError(
            "markdown_yield: both price-basis rows required; retain missing yields as blanks"
        )
    if not any(f.amount is not None for f in values):
        raise ValueError(
            "markdown_yield: at least one numeric observation required; missing is not zero"
        )
    typed = ReportTable(
        table_id=tid,
        title="Conditional maturity yield numeric view",
        row_header="Observation",
        columns=(TableColumn(field="value", label="Yield, %"),),
        rows=tuple(rows),
    )
    updated = module.model_copy(
        update={"facts": (*module.facts, *values), "tables": (*module.tables, typed)}
    )
    points.sort(key=lambda p: (p.category, p.series))
    return updated, tuple(dict.fromkeys(p.series for p in points)), tuple(points)


def _chart_cell(
    source: Fact, route: MarkdownRoute, stated_unit: str | None, module_id: str
) -> tuple[Decimal | None, bool, int | None]:
    """(amount, missing, display decimals) of one selected cell; a source that states another
    unit, a non-number or a non-finite value is refused, never retyped."""
    unit, scale, currency = CHART_TYPES[route.chart_unit or ""]
    default_decimals = 4 if route.chart_unit == "%" else 2
    if source.amount is not None or module_id == "CP-MODEL":
        if (
            source.unit != unit
            or source.scale != scale
            or (currency is not None and source.currency != currency)
            or (source.amount is not None and not source.amount.is_finite())
        ):
            raise ValueError("markdown_chart: typed source unit/currency differs")
        missing = source.status != "known"
        return (
            source.amount,
            missing,
            (source.decimals if source.amount is not None else default_decimals),
        )
    token = source.text or ""
    if (
        source.status != "known"
        or token in GAP_TOKENS
        or token.startswith(("Not supplied", "Not calculable"))
    ):
        return None, True, default_decimals
    if len(token) > 64 or not EXACT_NUMBER.fullmatch(token):
        raise ValueError(
            "markdown_chart: selected value must be an exact finite number or explicit gap"
        )
    if stated_unit and stated_unit != route.chart_unit:
        raise ValueError(
            f"markdown_chart: source {REPORTING_UNIT} {stated_unit!r} is not the chart unit "
            f"{route.chart_unit!r}; keep the value as a gap or select a matching table"
        )
    return exact_number(token), False, token_decimals(token, CHART_UNITS[route.chart_unit or ""])


def _check_chart_selectors(table: ReportTable, route: MarkdownRoute) -> list[str]:
    columns = [column.label for column in table.columns]
    labels = [row.label for row in table.rows]
    if (
        len(set(columns)) != len(columns)
        or len(set(labels)) != len(labels)
        or len(set(route.value_columns)) != len(route.value_columns)
        or len(set(route.row_labels)) != len(route.row_labels)
        or not set(route.value_columns) <= set(columns)
        or not set(route.row_labels) <= set(labels)
    ):
        raise ValueError("markdown_chart: unique source rows and columns must match selectors")
    return columns


@dataclass(frozen=True)
class _Cell:
    value: tuple[Decimal | None, bool, int | None]
    series: str
    category: str


def _chart_fact(index: int, tid: str, source: Fact, route: MarkdownRoute, cell: _Cell) -> Fact:
    amount, missing, decimals = cell.value
    unit, scale, currency = CHART_TYPES[route.chart_unit or ""]
    return Fact(
        fact_id=f"{tid}.r{index}.value",
        table_id=tid,
        row_id=f"r{index}",
        field="value",
        label=source.label,
        amount=amount,
        status="missing" if missing else "known",
        unit=unit,
        scale=scale,
        currency=currency,
        period=cell.category,
        decimals=decimals,
        citations=source.citations,
        limitation=(source.limitation or source.text or "Missing source observation")
        if missing
        else source.limitation,
        basis=source.basis or "Exact selected handoff value; no new financial calculation.",
        value_class=source.value_class,
        calculation_id=source.calculation_id,
        calculation_status=source.calculation_status,
        formula=source.formula,
        denominator=source.denominator,
    )


def _numeric_observations(
    module: ModuleView, table: ReportTable, route: MarkdownRoute
) -> tuple[ModuleView, tuple[str, ...], tuple[_ChartPoint, ...]]:
    """Copy explicitly selected cells into the existing charts without calculating finance."""
    columns = _check_chart_selectors(table, route)
    selected = [row for row in table.rows if not route.row_labels or row.label in route.row_labels]
    facts = {fact.fact_id: fact for fact in module.facts}
    tid = "chart-" + route.block_id + "-" + str(route.figure_id)
    values: list[Fact] = []
    rows: list[TableRow] = []
    points: list[_ChartPoint] = []
    for row in selected:
        stated = (
            (facts[row.fact_ids[columns.index(REPORTING_UNIT)]].text or "").strip()
            if REPORTING_UNIT in columns
            else None
        )
        for column in route.value_columns:
            source = facts[row.fact_ids[columns.index(column)]]
            if SHARE_QUANTITY.search(row.label) or SHARE_QUANTITY.search(column):
                raise ValueError(
                    "markdown_chart: share/per-share quantities are not monetary totals"
                )
            series, category = (
                (row.label, column)
                if route.orientation == "period-columns"
                else (column, row.label)
            )
            cell = _Cell(_chart_cell(source, route, stated, module.module_id), series, category)
            if module.module_id == "CP-MODEL":
                points.append(_ChartPoint(series=series, category=category, fact_id=source.fact_id))
                continue
            values.append(_chart_fact(len(values), tid, source, route, cell))
            fid = values[-1].fact_id
            rows.append(
                TableRow(row_id=f"r{len(rows)}", label=f"{series} · {category}", fact_ids=(fid,))
            )
            points.append(_ChartPoint(series=series, category=category, fact_id=fid))
    if not points:
        raise ValueError("markdown_chart: no selected observations")
    if module.module_id == "CP-MODEL":
        return module, tuple(dict.fromkeys(p.series for p in points)), tuple(points)
    typed = ReportTable(
        table_id=tid,
        title=route.label or table.title,
        row_header="Observation",
        columns=(TableColumn(field="value", label=route.chart_unit or "Value"),),
        rows=tuple(rows),
    )
    return (
        module.model_copy(
            update={"facts": (*module.facts, *values), "tables": (*module.tables, typed)}
        ),
        tuple(dict.fromkeys(p.series for p in points)),
        tuple(points),
    )


def require_issuer(run: Run, aliases: tuple[str, ...], module_id: str, lines: list[str]) -> None:
    """The handoff's title or Request section must name the run's issuer, as whole words."""
    request = " ".join(line for _, line in section(lines, "Request"))
    names = (run.issuer_name, *aliases, run.issuer_id)
    if not (names_issuer(lines[0], names) or names_issuer(request, names)):
        raise ValueError(
            "markdown_issuer: handoff title or Request must identify the selected issuer: "
            + module_id
        )


_FigureSpec = tuple[str, str, str, tuple[str, ...], tuple[_ChartPoint, ...]]


@dataclass
class _Assembly:
    """The literal modules of one delivery and the bindings routed from them so far."""

    modules: list[ModuleView]
    sources: list[Source]
    metadata: dict[str, dict[str, tuple[str, str]]]
    files: dict[str, bytes]
    entries: dict[str, list[Binding]] = field(default_factory=dict)
    used: set[tuple[str, str]] = field(default_factory=set)
    yield_charts: dict[str, tuple[str, tuple[str, ...], tuple[_ChartPoint, ...]]] = field(
        default_factory=dict
    )
    strip_charts: dict[str, dict[str, _FigureSpec]] = field(default_factory=dict)

    def module(self, module_id: str) -> ModuleView:
        return next(m for m in self.modules if m.module_id == module_id)

    def update(self, module: ModuleView, heading: str) -> ModuleView:
        """Replace a module with its typed copy, whose last table is the new chart table."""
        self.modules = [module if m.module_id == module.module_id else m for m in self.modules]
        self.metadata[module.module_id][module.tables[-1].table_id] = (heading, "chart")
        return module


def _validate_layout(request: DeliveryRequest, layout: MarkdownLayout, preset: Pathway) -> None:
    if len(set(layout.blocks)) != len(layout.blocks) or not set(layout.blocks) <= set(
        preset.blocks
    ):
        raise ValueError("markdown_layout: unique blocks must belong to the selected pathway")
    if {route.block_id for route in layout.routes} != set(layout.blocks):
        raise ValueError("markdown_layout: every requested block needs explicit handoff routes")
    if any(
        (
            r.module_id not in request.handoffs
            and not (r.module_id == "CP-MODEL" and request.model is not None)
        )
        or r.block_id not in layout.blocks
        for r in layout.routes
    ):
        raise ValueError("markdown_layout: routes must name supplied modules and selected blocks")
    if any(
        _spec_of(block_id).kind not in {"dense", "prose", "keyvalue", "period_grid"}
        and block_id not in {"yield-against-maturity", *STRIP_FIGURES}
        for block_id in layout.blocks
    ):
        raise ValueError("markdown_layout: literal presentation supports table and prose blocks")
    if any(
        route.kind in {"table", "chart"}
        and (route.prefix is not None or _spec_of(route.block_id).kind == "prose")
        for route in layout.routes
    ):
        raise ValueError("markdown_layout: preserve complete table columns in a table block")
    if any(
        route.kind != "chart"
        and route.block_id != "yield-against-maturity"
        and _spec_of(route.block_id).kind == "chart"
        for route in layout.routes
    ):
        raise ValueError(
            "markdown_layout: a chart block shows only chart routes; route tables and prose "
            "to a table or prose block"
        )


def _load_modules(request: DeliveryRequest, layout: MarkdownLayout, base: Path) -> _Assembly:
    assembly = _Assembly(modules=[], sources=[], metadata={}, files={})
    for module_id, spec in request.handoffs.items():
        raw = (base / spec.path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != spec.sha256:
            raise ValueError(f"Changed handoff: {module_id}")
        require_issuer(request.run, layout.issuer_aliases, module_id, raw.decode().splitlines())
        module, source, meta = literal_module(module_id, raw)
        assembly.modules.append(module)
        assembly.sources.append(source)
        assembly.metadata[module_id] = meta
        assembly.files[module_id + ".md"] = raw
    if request.model is not None:
        _load_model(request, base, assembly)
    assembly.entries = {m.module_id: [] for m in assembly.modules}
    return assembly


def _load_model(request: DeliveryRequest, base: Path, assembly: _Assembly) -> None:
    from deploy_workflow.model_handoff_delivery import build_model

    assert request.model is not None
    if not {"CP-1", "CP-2"} <= set(request.handoffs) or "CP-MODEL" in request.handoffs:
        raise ValueError("markdown_model: annual CP-1 and current CP-2 handoffs required")
    if set(request.model.extra_handoffs) - {"quarter", "forecast"}:
        raise ValueError("model_inputs: unknown extra handoff role")
    inputs = {
        "annual": request.handoffs["CP-1"],
        "current_synthesis": request.handoffs["CP-2"],
        **request.model.extra_handoffs,
    }
    if request.model.forecast_exact is not None:
        inputs["forecast_exact"] = request.model.forecast_exact
    publication = build_model(
        request.run,
        inputs,
        {k: (base / v.path).read_bytes() for k, v in inputs.items()},
        request.model,
    )
    assembly.modules.append(publication.module)
    assembly.sources.extend(publication.sources)
    assembly.files.update(publication.files)
    assembly.metadata["CP-MODEL"] = {
        t.table_id: (t.title, "table") for t in publication.module.tables
    }


def _route_table(assembly: _Assembly, route: MarkdownRoute) -> tuple[ModuleView, ReportTable]:
    module = assembly.module(route.module_id)
    tables = [
        t
        for t in module.tables
        if assembly.metadata[module.module_id][t.table_id]
        == (route.heading, "table" if route.kind == "chart" else route.kind)
        and (route.table_header is None or t.row_header == route.table_header)
        and (route.kind != "chart" or set(route.value_columns) <= {c.label for c in t.columns})
    ]
    if len(tables) != 1:
        raise ValueError(
            f"markdown_selector: expected one {route.module_id}/{route.heading}/"
            f"{route.table_header}"
        )
    return module, tables[0]


def _bind_chart(
    assembly: _Assembly, route: MarkdownRoute, module: ModuleView, table: ReportTable
) -> None:
    if route.figure_id not in STRIP_FIGURES.get(route.block_id, ()):
        raise ValueError("markdown_chart: figure does not belong to this pathway block")
    figure_specs = assembly.strip_charts.setdefault(route.block_id, {})
    if route.figure_id in figure_specs:
        raise ValueError("markdown_chart: exactly one selector per figure")
    updated, series, points = _numeric_observations(module, table, route)
    if module.module_id != "CP-MODEL":
        typed = assembly.update(updated, route.heading).tables[-1]
        assembly.entries[module.module_id].append(
            Binding(
                fact_coord=FactCoord(module_id=module.module_id, table_id=typed.table_id),
                block_id=route.block_id,
                cell_slot=route.figure_id,
                unit_class=CHART_UNITS[route.chart_unit or ""],
            )
        )
        assembly.used.update((module.module_id, point.fact_id) for point in points)
    figure_specs[route.figure_id] = (
        module.module_id,
        route.label or table.title,
        route.chart_unit or "",
        series,
        points,
    )


def _bind_yield(assembly: _Assembly, route: MarkdownRoute, table: ReportTable, as_of: date) -> None:
    if route.kind != "table" or route.block_id in assembly.yield_charts:
        raise ValueError("markdown_yield: exactly one complete source table required")
    module = assembly.module(route.module_id)
    updated, series, points = _yield_observations(module, table, as_of)
    typed = assembly.update(updated, route.heading).tables[-1]
    assembly.entries[module.module_id].append(
        Binding(
            fact_coord=FactCoord(module_id=module.module_id, table_id=typed.table_id),
            block_id=route.block_id,
            cell_slot="conditional-yield",
            unit_class="percent",
        )
    )
    assembly.used.update((module.module_id, p.fact_id) for p in points)
    assembly.yield_charts[route.block_id] = (module.module_id, series, points)


def _unused_rows(
    assembly: _Assembly, route: MarkdownRoute, module: ModuleView, table: ReportTable
) -> list[TableRow]:
    facts = {f.fact_id: f for f in module.facts}
    selected = [
        r
        for r in table.rows
        if all((module.module_id, fid) not in assembly.used for fid in r.fact_ids)
        and (
            route.prefix is None or plain(facts[r.fact_ids[0]].text or "").startswith(route.prefix)
        )
    ]
    if not selected:
        raise ValueError(f"markdown_selector: no unused content for {route.heading}")
    return selected


def _bind_rows(
    assembly: _Assembly,
    route: MarkdownRoute,
    module: ModuleView,
    table: ReportTable,
    selected: list[TableRow],
) -> None:
    entries = assembly.entries[module.module_id]
    groups = [None] if len(selected) == len(table.rows) else [r.row_id for r in selected]
    for row_id in groups:
        entries.append(
            Binding(
                fact_coord=FactCoord(
                    module_id=module.module_id, table_id=table.table_id, row_id=row_id
                ),
                block_id=route.block_id,
                cell_slot=f"{module.module_id}-{len(entries)}",
                unit_class=("amount" if table.table_id == "history" else "multiple")
                if module.module_id == "CP-MODEL" and table.table_id in {"history", "ratios"}
                else "text",
                label=route.label or table.title,
            )
        )
    assembly.used.update((module.module_id, fid) for r in selected for fid in r.fact_ids)


def _bind_route(assembly: _Assembly, route: MarkdownRoute, as_of: date) -> None:
    module, table = _route_table(assembly, route)
    if route.kind == "chart":
        _bind_chart(assembly, route, module, table)
        return
    selected = _unused_rows(assembly, route, module, table)
    if route.block_id == "yield-against-maturity":
        _bind_yield(assembly, route, table, as_of)
        return
    _bind_rows(assembly, route, module, table, selected)


def _bind_evidence(assembly: _Assembly) -> None:
    """Every row no route used goes to the existing Evidence block, never dropped."""
    for module in assembly.modules:
        entries = assembly.entries[module.module_id]
        for table in module.tables:
            remaining = [
                r
                for r in table.rows
                if all((module.module_id, fid) not in assembly.used for fid in r.fact_ids)
            ]
            groups = [None] if len(remaining) == len(table.rows) else [r.row_id for r in remaining]
            for row_id in groups:
                entries.append(
                    Binding(
                        fact_coord=FactCoord(
                            module_id=module.module_id, table_id=table.table_id, row_id=row_id
                        ),
                        block_id="evidence",
                        cell_slot=f"{module.module_id}-{len(entries)}",
                        unit_class="text",
                    )
                )


@dataclass(frozen=True)
class _Composition:
    """What every block builder reads: the assembly, its view, references and block notes."""

    assembly: _Assembly
    view: View
    refs: dict[tuple[str, str], tuple[str, ...]]
    layout: MarkdownLayout


def _strip_block(composition: _Composition, block_id: str, title: str) -> Block:
    specs = composition.assembly.strip_charts[block_id]
    if set(specs) != set(STRIP_FIGURES[block_id]):
        raise ValueError(
            "markdown_chart: supply every requested strip figure, preserving explicit gaps"
        )
    figures = []
    for fig_id in STRIP_FIGURES[block_id]:
        module_id, figure_title, unit, series, points = specs[fig_id]
        figures.append(
            _figure_of_points(
                block_id,
                composition.assembly.module(module_id),
                composition.refs,
                fig_id=fig_id,
                title=figure_title,
                kind="grouped" if fig_id in {"S.4", "RV.1"} else "line",
                unit_class=CHART_UNITS[unit],
                unit=unit,
                series=series,
                points=points,
                placement="above",
                summary=STRIP_SUMMARY,
            )
        )
    return Block(
        block_id=block_id,
        title=title,
        kind="chart",
        owner=" · ".join(dict.fromkeys(spec[0] for spec in specs.values())),
        state="populated",
        full_analysis_route=next(iter(specs.values()))[0],
        width="full",
        figures=tuple(figures),
    )


def _yield_block(composition: _Composition, block_id: str, title: str, owner: str) -> Block:
    if block_id not in composition.assembly.yield_charts:
        raise ValueError("markdown_chart: explicit numeric selectors required for each figure")
    module_id, series, points = composition.assembly.yield_charts[block_id]
    figure = _figure_of_points(
        block_id,
        composition.assembly.module(module_id),
        composition.refs,
        fig_id="RV.1",
        title="Conditional maturity yield by note maturity",
        kind="line",
        unit_class="percent",
        unit="%",
        series=series,
        points=points,
        placement="above",
        summary=YIELD_SUMMARY,
    )
    return Block(
        block_id=block_id,
        title=title,
        kind="chart",
        owner=owner,
        state="populated",
        full_analysis_route=module_id,
        width="full",
        figures=(figure,),
    )


def _table_block(
    composition: _Composition, block_id: str, bound: tuple[Binding, ...], note: str | None
) -> Block:
    block_spec = _spec_of(block_id)
    owner = " · ".join(dict.fromkeys(e.fact_coord.module_id for e in bound))
    if block_spec.kind == "prose":
        return Block(
            block_id=block_id,
            title=block_spec.title,
            kind="prose",
            owner=owner,
            state="populated",
            full_analysis_route=bound[0].fact_coord.module_id,
            width="full",
            lines=_prose_lines(bound, composition.view, composition.refs),
            note=note,
        )
    slots = (
        _slot(e, composition.assembly.module(e.fact_coord.module_id), composition.refs)
        for e in bound
    )
    primary = next(slots)
    tabs = tuple(
        BlockTab(label=s.label, row_header=s.row_header, columns=s.columns, rows=s.rows)
        for s in slots
    )
    return Block(
        block_id=block_id,
        title=block_spec.title,
        kind=block_spec.kind,
        owner=owner,
        state="populated",
        full_analysis_route=bound[0].fact_coord.module_id,
        width="full",
        row_header=primary.row_header,
        columns=primary.columns,
        rows=primary.rows,
        note=note,
        tab_label=primary.label if tabs else None,
        tabs=tabs,
    )


def _block_for(composition: _Composition, block_id: str) -> Block:
    assembly = composition.assembly
    bound = tuple(e for items in assembly.entries.values() for e in items if e.block_id == block_id)
    if not bound and block_id not in assembly.strip_charts:
        raise ValueError(f"markdown_content: selected block has no handoff content: {block_id}")
    block_spec = _spec_of(block_id)
    if block_spec.kind != "chart":
        note = (
            " · ".join(
                dict.fromkeys(
                    r.label for r in composition.layout.routes if r.block_id == block_id and r.label
                )
            )
            or None
        )
        return _table_block(composition, block_id, bound, note)
    if block_id in assembly.strip_charts:
        return _strip_block(composition, block_id, block_spec.title)
    owner = " · ".join(dict.fromkeys(e.fact_coord.module_id for e in bound))
    return _yield_block(composition, block_id, block_spec.title, owner)


def _report(
    request: DeliveryRequest, preset: Pathway, assembly: _Assembly
) -> tuple[View, ReportView]:
    layout = request.layout
    assert layout is not None
    view = View(
        run=request.run,
        mode="candidate",
        modules=tuple(assembly.modules),
        sources=tuple(assembly.sources),
        analytical_qualification="partial",
        native_host_qualification="unrun",
    )
    maps = tuple(
        BindingMap(module_id=module_id, entries=tuple(items))
        for module_id, items in assembly.entries.items()
    )
    if issues := validate_bindings(view, maps):
        raise ValueError("markdown_bindings: " + "; ".join(issues))
    pathway = preset.model_copy(
        update={
            "blocks": layout.blocks,
            "requested_modules": request.run.requested_modules,
            "title": layout.title or preset.title,
            "question": layout.question or preset.question,
        }
    )
    passports, index = build_index(view)
    composition = _Composition(assembly, view, _refs_by_fact(index), layout)
    blocks = tuple(_block_for(composition, block_id) for block_id in layout.blocks)
    call, withheld = _call({m.module_id: m for m in assembly.modules}, pathway)
    posture = _portfolio_call(
        next((m for m in assembly.modules if m.module_id == "CP-6"), None),
        assembly.metadata.get("CP-6", {}),
        composition.refs,
        portfolio=pathway.id == "portfolio_decision",
    )
    if posture is not None:
        call, withheld = (posture,), None
    if "CP-6" not in request.handoffs:
        withheld = "not_requested"
    report = ReportView(
        pathway=pathway,
        call=call,
        call_withheld=withheld,
        blocks=blocks,
        passports=passports,
        index=index,
        unplaced=_unplaced(view, pathway, maps),
    )
    return view, report


def markdown_files(request: DeliveryRequest, base: Path) -> dict[str, bytes]:
    """Select literal source sections into the existing requested pathway design."""
    layout = request.layout
    if layout is None:
        raise ValueError("markdown_layout: select explicit presentation routes")
    preset = next(p for p in pathways() if p.id == request.run.pathway)
    _validate_layout(request, layout, preset)
    assembly = _load_modules(request, layout, base)
    for route in layout.routes:
        _bind_route(assembly, route, request.run.as_of)
    _bind_evidence(assembly)
    view, report = _report(request, preset, assembly)
    has_model = request.model is not None
    rendered = with_scope_banner(
        render(view, report),
        layout.scope,
        model_nav="model.html" if has_model else None,
        deliverables_nav=has_model,
    )
    files = assembly.files
    files.update(
        {
            "view.json": view.model_dump_json(indent=2).encode(),
            "report-view.json": report.model_dump_json(indent=2).encode(),
            "report.html": rendered.encode(),
        }
    )
    record = {
        "kind": "literal_handoff_delivery",
        "scope": layout.scope,
        "analytical_runtime_executed": False,
        "cp_model_published": has_model,
        "excel_output": False,
        "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
    }
    files["delivery.json"] = (json.dumps(record, indent=2) + "\n").encode()
    return files
