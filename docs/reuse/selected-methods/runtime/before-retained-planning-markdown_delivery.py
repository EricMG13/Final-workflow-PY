"""Literal Markdown-to-report adapter, separate from native analytical contracts.

Existing report/index/table/prose components own presentation. This adapter
retains the actual handoffs, text and source lines; it performs no financial
calculation, journal promotion or analytical execution.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

from deploy_vii.bindings import Binding, BindingMap, validate_bindings
from deploy_vii.contracts import (
    Citation,
    Fact,
    ModuleView,
    ReportTable,
    Source,
    TableColumn,
    TableRow,
    View,
)
from deploy_vii.registry import modules
from deploy_vii.render import render
from deploy_vii.report_view import (
    Block,
    BlockTab,
    FactCoord,
    ReportView,
    _call,
    _prose_lines,
    _refs_by_fact,
    _slot,
    _spec_of,
    _unplaced,
    build_index,
    pathways,
)
from deploy_workflow.handoff_delivery import DeliveryRequest, plain


def literal_module(
    module_id: str, raw: bytes
) -> tuple[ModuleView, Source, dict[str, tuple[str, str]]]:
    """Retain tables and wrapped prose with exact physical-line citations."""
    from deploy_workflow.model_handoff_delivery import _literal_tables

    digest = hashlib.sha256(raw).hexdigest()
    source, facts, tables, _ = _literal_tables(module_id, raw, digest)
    lines = raw.decode("utf-8").splitlines()
    headings = [
        (n, line.lstrip("#").strip()) for n, line in enumerate(lines, 1) if line.startswith("#")
    ]
    metadata: dict[str, tuple[str, str]] = {}
    fact_map = {f.fact_id: f for f in facts}
    for i, table in enumerate(tables):
        first = fact_map[table.rows[0].fact_ids[0]].citations[0]
        number = int(first.locator.split()[-1])
        heading = next(title for n, title in reversed(headings) if n < number)
        tables[i] = table.model_copy(
            update={"title": heading + " — " + (table.row_header or "Table")}
        )
        metadata[table.table_id] = (heading, "table")
    paragraphs: dict[str, list[list[tuple[int, str]]]] = {}
    heading = "Document"
    pending: list[tuple[int, str]] = []
    for number, line in enumerate([*lines, ""], 1):
        boundary = not line.strip() or line.startswith(("#", "|", "<!--"))
        if boundary and pending:
            paragraphs.setdefault(heading, []).append(pending)
            pending = []
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        elif not boundary:
            pending.append((number, line))
    for index, (heading, groups) in enumerate(paragraphs.items()):
        table_id = f"prose-{module_id}-{index}"
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
                    text=plain(" ".join(line.strip() for _, line in paragraph)),
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
        tables.append(
            ReportTable(
                table_id=table_id,
                title=heading,
                row_header="Paragraph",
                columns=(TableColumn(field="c0", label="Text"),),
                rows=tuple(rows),
            )
        )
        metadata[table_id] = (heading, "prose")
    descriptor = next(m for m in modules() if m.module_id == module_id)
    return (
        ModuleView(
            module_id=module_id,
            title=descriptor.title,
            aliases=descriptor.aliases,
            status="candidate",
            artifact_sha256=digest,
            facts=tuple(facts),
            tables=tuple(tables),
            limitations=(
                "Literal checked analytical handoff, not native contract acceptance; source qualifications and gaps remain.",
            ),
        ),
        source,
        metadata,
    )


def markdown_files(request: DeliveryRequest, base: Path) -> dict[str, bytes]:
    """Select literal source sections into the existing requested pathway design."""
    layout = request.layout
    if layout is None or request.model is not None:
        raise ValueError(
            "markdown_layout: select literal presentation without the annual Model adapter"
        )
    preset = next(p for p in pathways() if p.id == request.run.pathway)
    if len(set(layout.blocks)) != len(layout.blocks) or not set(layout.blocks) <= set(
        preset.blocks
    ):
        raise ValueError("markdown_layout: unique blocks must belong to the selected pathway")
    if any(
        r.module_id not in request.handoffs or r.block_id not in layout.blocks
        for r in layout.routes
    ):
        raise ValueError("markdown_layout: routes must name supplied modules and selected blocks")
    if any(_spec_of(block_id).kind not in {"dense", "prose"} for block_id in layout.blocks):
        raise ValueError("markdown_layout: literal presentation supports table and prose blocks")
    if any(
        route.kind == "table"
        and (route.prefix is not None or _spec_of(route.block_id).kind == "prose")
        for route in layout.routes
    ):
        raise ValueError("markdown_layout: preserve complete table columns in a table block")
    module_views = []
    sources = []
    metadata = {}
    files = {}
    for module_id, spec in request.handoffs.items():
        raw = (base / spec.path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != spec.sha256:
            raise ValueError(f"Changed handoff: {module_id}")
        title = raw.decode().splitlines()[0].casefold()
        if request.run.issuer_name.casefold() not in title and not re.search(
            r"(?<![a-z0-9])" + re.escape(request.run.issuer_id.casefold()) + r"(?![a-z0-9])", title
        ):
            raise ValueError(
                f"markdown_issuer: handoff title must identify the selected issuer: {module_id}"
            )
        module, source, meta = literal_module(module_id, raw)
        module_views.append(module)
        sources.append(source)
        metadata[module_id] = meta
        files[module_id + ".md"] = raw
    entries: dict[str, list[Binding]] = {m.module_id: [] for m in module_views}
    used: set[tuple[str, str]] = set()
    for route in layout.routes:
        module = next(m for m in module_views if m.module_id == route.module_id)
        tables = [
            t
            for t in module.tables
            if metadata[module.module_id][t.table_id] == (route.heading, route.kind)
            and (route.table_header is None or t.row_header == route.table_header)
        ]
        if len(tables) != 1:
            raise ValueError(
                f"markdown_selector: expected one {route.module_id}/{route.heading}/{route.table_header}"
            )
        table = tables[0]
        facts = {f.fact_id: f for f in module.facts}
        selected = [
            r
            for r in table.rows
            if all((module.module_id, fid) not in used for fid in r.fact_ids)
            and (
                route.prefix is None
                or plain(facts[r.fact_ids[0]].text or "").startswith(route.prefix)
            )
        ]
        if not selected:
            raise ValueError(f"markdown_selector: no unused content for {route.heading}")
        groups = [None] if len(selected) == len(table.rows) else [r.row_id for r in selected]
        for row_id in groups:
            entries[module.module_id].append(
                Binding(
                    fact_coord=FactCoord(
                        module_id=module.module_id, table_id=table.table_id, row_id=row_id
                    ),
                    block_id=route.block_id,
                    cell_slot=f"{module.module_id}-{len(entries[module.module_id])}",
                    unit_class="text",
                    label=route.label or table.title,
                )
            )
        used.update((module.module_id, fid) for r in selected for fid in r.fact_ids)
    for module in module_views:
        for table in module.tables:
            remaining = [
                r
                for r in table.rows
                if all((module.module_id, fid) not in used for fid in r.fact_ids)
            ]
            groups = [None] if len(remaining) == len(table.rows) else [r.row_id for r in remaining]
            for row_id in groups:
                entries[module.module_id].append(
                    Binding(
                        fact_coord=FactCoord(
                            module_id=module.module_id, table_id=table.table_id, row_id=row_id
                        ),
                        block_id="evidence",
                        cell_slot=f"{module.module_id}-{len(entries[module.module_id])}",
                        unit_class="text",
                    )
                )
    view = View(
        run=request.run,
        mode="candidate",
        modules=tuple(module_views),
        sources=tuple(sources),
        analytical_qualification="partial",
        native_host_qualification="unrun",
    )
    maps = tuple(
        BindingMap(module_id=module_id, entries=tuple(items))
        for module_id, items in entries.items()
    )
    if issues := validate_bindings(view, maps):
        raise ValueError("markdown_bindings: " + "; ".join(issues))
    pathway = preset.model_copy(
        update={"blocks": layout.blocks, "requested_modules": request.run.requested_modules}
    )
    passports, index = build_index(view)
    refs = _refs_by_fact(index)
    blocks = []
    for block_id in layout.blocks:
        bound = tuple(e for items in entries.values() for e in items if e.block_id == block_id)
        if not bound:
            raise ValueError(f"markdown_content: selected block has no handoff content: {block_id}")
        block_spec = _spec_of(block_id)
        owner = " · ".join(dict.fromkeys(e.fact_coord.module_id for e in bound))
        if block_spec.kind == "prose":
            blocks.append(
                Block(
                    block_id=block_id,
                    title=block_spec.title,
                    kind="prose",
                    owner=owner,
                    state="populated",
                    full_analysis_route=bound[0].fact_coord.module_id,
                    width="full",
                    lines=_prose_lines(bound, view, refs),
                )
            )
        else:
            slots = [
                _slot(
                    e, next(m for m in module_views if m.module_id == e.fact_coord.module_id), refs
                )
                for e in bound
            ]
            primary = slots[0]
            tabs = tuple(
                BlockTab(label=s.label, row_header=s.row_header, columns=s.columns, rows=s.rows)
                for s in slots[1:]
            )
            blocks.append(
                Block(
                    block_id=block_id,
                    title=block_spec.title,
                    kind="dense",
                    owner=owner,
                    state="populated",
                    full_analysis_route=bound[0].fact_coord.module_id,
                    width="full",
                    row_header=primary.row_header,
                    columns=primary.columns,
                    rows=primary.rows,
                    tab_label=primary.label if tabs else None,
                    tabs=tabs,
                )
            )
    call, withheld = _call({m.module_id: m for m in module_views}, pathway)
    if "CP-6" not in request.handoffs:
        withheld = "not_requested"
    report = ReportView(
        pathway=pathway,
        call=call,
        call_withheld=withheld,
        blocks=tuple(blocks),
        passports=passports,
        index=index,
        unplaced=_unplaced(view, pathway, maps),
    )
    rendered = render(view, report)
    anchor = '<div id="call-root"></div>'
    if rendered.count(anchor) != 1:
        raise ValueError("Existing renderer scope-banner location changed")
    files.update(
        {
            "view.json": view.model_dump_json(indent=2).encode(),
            "report-view.json": report.model_dump_json(indent=2).encode(),
            "report.html": rendered.replace(
                anchor,
                '<section id="delivery-scope-banner" class="banner" role="note">'
                + html.escape(layout.scope)
                + "</section>"
                + anchor,
            ).encode(),
        }
    )
    record = {
        "kind": "literal_handoff_delivery",
        "scope": layout.scope,
        "analytical_runtime_executed": False,
        "cp_model_published": False,
        "excel_output": False,
        "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
    }
    files["delivery.json"] = (json.dumps(record, indent=2) + "\n").encode()
    return files
