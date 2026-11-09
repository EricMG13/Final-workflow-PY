"""Copy checked Markdown handoffs into the existing report designs.

This is a narrow presentation adapter, not an analytical runner or journal import.
Narrative values stay literal, with citations to exact model-authored handoff
lines. Optional CP-MODEL publication reuses the existing calculation and chart
components through explicit source selectors; Excel is ingestion-only.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import (
    Citation,
    Contract,
    Fact,
    Hash,
    ModuleView,
    ReportTable,
    Run,
    Source,
    Span,
    TableColumn,
    TableRow,
    View,
)
from deploy_vii.registry import modules
from deploy_vii.render import render
from deploy_vii.report_view import FactCoord, ReportView, build, pathways
from deploy_workflow.run_scopes import PUBLIC_S1A_MODULES

HEADINGS = ("Request", "Sources", "Findings", "Calculations", "Gaps", "Next module")
SECTIONS = (
    "key-findings",
    "company-operating-model",
    "strengths-weaknesses",
    "company-profile",
    "transaction-summary",
)
SCOPE = (
    "Manual delivery from checked, model-authored Markdown handoffs. Historical financial "
    "base: {as_of}; disclosed subsequent events remain separately identified. "
    "Five narrative sections only. CP-MODEL, charts, committee decision, "
    "automated orchestration and the full pathway remain unproven. "
    "Citations identify handoff lines, whose issuer references and limitations are retained."
)
MODEL_SCOPE = (
    "Delivery from checked Markdown handoffs. Historical annual financial base: {as_of}; "
    "subsequent events, additional quarter windows and conditional scenarios remain separate. "
    "Five narrative sections plus the HTML Model, charts and calculation JSON are published. "
    "Missing data and analytical limitations remain explicit. Complete current underwriting, "
    "committee action and broader pathways are outside this publication."
)


class HandoffInput(Contract):
    path: str
    sha256: Hash


class ModelPeriod(Contract):
    start_date: date
    end_date: date
    balance_column: str | None


class ModelRow(Contract):
    table: str
    label: str


class DerivedRows(Contract):
    """Request to publish the grid's derived rows; the debt register is matched like anchors."""

    debt_register: str | None = None
    quarter_bridge: str | None = Field(default=None, exclude_if=lambda v: v is None)
    quarter_debt_register: str | None = Field(default=None, exclude_if=lambda v: v is None)


class ModelDelivery(Contract):
    """Explicit source selectors for the selected annual CP-1 publication method."""

    periods: dict[str, ModelPeriod] = Field(min_length=1)
    anchors: dict[str, str]
    rows: dict[str, ModelRow]
    extra_handoffs: dict[str, HandoffInput] = Field(default_factory=dict)
    forecast_exact: HandoffInput | None = None
    derived: DerivedRows | None = Field(default=None, exclude_if=lambda v: v is None)


class MarkdownRoute(Contract):
    module_id: str
    heading: str
    kind: Literal["table", "prose", "chart"]
    block_id: str
    table_header: str | None = None
    prefix: str | None = None
    label: str | None = None
    figure_id: Literal["S.1", "S.2", "S.3", "S.4", "RV.1"] | None = None
    value_columns: tuple[str, ...] = ()
    row_labels: tuple[str, ...] = ()
    orientation: Literal["period-columns", "period-rows"] = "period-columns"
    chart_unit: Literal["x", "US$m", "%"] | None = None

    @model_validator(mode="after")
    def chart_selection(self) -> MarkdownRoute:
        if self.kind == "chart":
            if (
                self.figure_id is None
                or not self.value_columns
                or self.chart_unit
                != (
                    {"S.1": "x", "S.2": "x", "S.3": "US$m", "S.4": "US$m", "RV.1": "%"}.get(
                        self.figure_id
                    )
                )
                or (
                    self.figure_id == "RV.1"
                    and any(not c.endswith("_fraction") for c in self.value_columns)
                )
                or self.prefix is not None
            ):
                raise ValueError("markdown_chart: select an explicit figure, columns and its unit")
        elif (
            self.figure_id is not None
            or self.value_columns
            or self.row_labels
            or self.chart_unit
            or self.orientation != "period-columns"
        ):
            raise ValueError("markdown_chart: numeric selectors require a chart route")
        return self


class MarkdownLayout(Contract):
    """Presentation selectors, not a replacement analytical schema or execution plan."""

    blocks: tuple[str, ...] = Field(min_length=1)
    routes: tuple[MarkdownRoute, ...] = Field(min_length=1)
    scope: str = Field(min_length=1)
    title: Annotated[str, Field(pattern=r"\S")] | None = None
    question: Annotated[str, Field(pattern=r"\S")] | None = None
    issuer_aliases: tuple[Annotated[str, Field(pattern=r"\S")], ...] = ()
    # Lines the report states above the call (kind "table" or "prose"); their `block_id` is not
    # a report block.
    front: tuple[MarkdownRoute, ...] = Field(default=(), exclude_if=lambda v: not v)


class DeliveryRequest(Contract):
    run: Run
    handoffs: dict[str, HandoffInput]
    model: ModelDelivery | None = None
    layout: MarkdownLayout | None = None
    module_execution: (
        dict[str, Literal["host-session", "retained-response-replay", "synthetic", "live-provider"]]
        | None
    ) = Field(default=None, exclude_if=lambda v: v is None)


SOURCE_NUMBER = re.compile(
    r"(?:-?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?"
    r"|\((?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?\))"
)


def is_gap(token: str) -> bool:
    """Whether a copied table cell is an explicit gap (blank, dash or an authored not-supplied)."""
    return token in {"", "—", "Insufficient Information", "Not reconstructed"} or token.startswith(
        ("Not supplied", "Not calculable")
    )


def physical_lines(text: str) -> list[str]:
    """The text's lines split on newlines only (`\\r\\n` and a lone `\\r` count as one), so a
    "line N" citation is the line a reader opens; `str.splitlines()` also splits on U+2028,
    U+2029, form feed, vertical tab, U+0085 and the separators U+001C to U+001E."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines[-1]:
        lines.pop()
    return lines


def plain(text: str) -> str:
    """Remove the supported inline emphasis only; never parse/reformat figures."""
    return re.sub(r"\*\*([^*]+)\*\*|`([^`]+)`", lambda m: m[1] or m[2], text).strip()


HEADING_LINE = re.compile(r"(#{1,6})(?:[ \t]+(.*?))?[ \t]*")


def heading_of(line: str) -> tuple[int, str] | None:
    """Level and text of an ATX heading; `#1 risk` and seven or more hashes are prose."""
    found = HEADING_LINE.fullmatch(line)
    return None if found is None else (len(found[1]), found[2] or "")


FENCE = re.compile(r"[ \t]*(?:`{3,}|~{3,})")


def comment_opener(line: str) -> int | None:
    """Index of the `<!--` that is still open at the end of `line`, else None: the first `<!--`
    after the last `-->`, anywhere in the line (a later nested one is inside the comment). Inline
    code spans are blanked first, as Markdown reads `<!--` inside them literally."""
    plain_text = re.sub(r"(`+).+?\1", lambda m: "x" * len(m[0]), line)
    closed = plain_text.rfind("-->")
    opener = plain_text.find("<!--", 0 if closed < 0 else closed + 3)
    return None if opener < 0 else opener


def hide_comments(lines: list[str], name: str) -> list[str]:
    """The lines with each multi-line HTML comment blanked through its `-->`, as Markdown viewers
    hide it, so no table or prose inside it is published; fenced text is left as written. A
    comment may open anywhere in a line; the opening line keeps the text before its `<!--` (blank
    when that is only spaces). Line numbers are unchanged. A comment that is never closed would
    hide the rest of the handoff: refused."""
    shown, fenced, opened = [], False, 0
    for number, line in enumerate(lines, 1):
        if opened:  # Inside a comment: hidden through its `-->`, and another may open after it.
            _, closed, rest = line.partition("-->")
            opened = (number if comment_opener(rest) is not None else 0) if closed else opened
            shown.append("")
            continue
        found = heading_of(line)
        fenced = fenced and not (found and found[0] == 2)  # A fence ends at a section.
        if FENCE.match(line):
            fenced = not fenced
        start = None if fenced else comment_opener(line)
        if start is None or FENCE.match(line):
            shown.append(line)
        else:
            opened = number
            shown.append(line[:start] if line[:start].strip() else "")
    if opened:
        raise ValueError(f"{name}: the HTML comment opened on line {opened} is never closed by -->")
    return shown


def hide_fenced(lines: list[str]) -> list[str]:
    """The lines with each fenced code block, fence lines included, blanked, so no table or
    heading inside one is read as such. A fence ends at the next section heading, as in
    `hide_comments`. Line numbers are unchanged."""
    shown, fenced = [], False
    for line in lines:
        found = heading_of(line)
        fenced = fenced and not (found and found[0] == 2)
        toggled = FENCE.match(line) is not None
        if toggled:
            fenced = not fenced
        shown.append("" if fenced or toggled else line)
    return shown


def names_issuer(text: str, names: tuple[str, ...]) -> bool:
    """Whether any non-blank name occurs in `text` as whole words, ignoring case and spacing.

    `Ford` is not in `Stanford` and the alias `AB` is not in `lab`: a name must not touch a
    letter or digit on either side.
    """
    haystack = " ".join(text.split()).casefold()
    return any(
        re.search(rf"(?<![^\W_]){re.escape(wanted)}(?![^\W_])", haystack) is not None
        for name in names
        if (wanted := " ".join(name.split()).casefold())
    )


def section(
    lines: list[str], title: str, levels: tuple[int, ...] = (2, 3)
) -> list[tuple[int, str]]:
    headings = tuple("#" * level + f" {title}" for level in levels)
    matches = [i for i, line in enumerate(lines) if line in headings]
    if len(matches) != 1:
        raise ValueError(f"Expected one Markdown section: {title}")
    start = matches[0]
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    boundaries = tuple("#" * size + " " for size in range(1, level + 1))
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith(boundaries)),
        len(lines),
    )
    return [(i + 1, lines[i]) for i in range(start + 1, end)]


TABLE_ROW = re.compile(r" {0,3}(\|.*?)\s*")


def table_row(text: str) -> str | None:
    """The row text of a line that starts with '|' after at most three spaces (four is code),
    without trailing whitespace; None for any other line."""
    found = TABLE_ROW.fullmatch(text)
    return None if found is None else found[1]


def table(rows: list[tuple[int, str]]) -> tuple[list[str], list[tuple[int, str, list[str]]]]:
    """Read the first contiguous pipe table in a named section, preserving cells."""
    selected = []
    for line, line_text in rows:
        text = table_row(line_text)
        if text is not None:
            selected.append((line, text))
        elif selected:
            break

    def cells(text: str) -> list[str]:
        if not text.endswith("|"):
            raise ValueError("Markdown table rows require both boundary pipes")
        return [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", text[1:-1])]

    if len(selected) < 3:
        raise ValueError("Expected a populated Markdown table")
    headers = cells(selected[0][1])
    separator = cells(selected[1][1])
    if (
        len(headers) < 2
        or len(separator) != len(headers)
        or not all(re.fullmatch(r":?-{3,}:?", c) for c in separator)
    ):
        raise ValueError("Invalid Markdown table header")
    result = [(line, raw, cells(raw)) for line, raw in selected[2:]]
    if any(len(values) != len(headers) or not values[0] for _, _, values in result):
        raise ValueError("Markdown table row does not match its header")
    return headers, result


def mapped_module(  # noqa: C901, PLR0915 - pre-existing size (C901 18, 62 statements at base)
    module_id: str, raw: bytes
) -> tuple[ModuleView, Source]:
    """Map this handoff revision's named sections without reinterpreting analysis."""
    text = raw.decode("utf-8")
    lines = physical_lines(text)
    if tuple(line[3:] for line in lines if line.startswith("## ")) != HEADINGS:
        raise ValueError(f"{module_id}: the six handoff headings are required once, in order")
    sha = hashlib.sha256(raw).hexdigest()
    source_id = module_id + "-handoff"
    source = Source(
        source_id=source_id,
        name=f"{module_id} model-authored Markdown handoff",
        status="ready",
        sha256=sha,
        media_type="text/markdown",
        extractor="literal-markdown-lines",
        extraction_status="complete",
        spans=tuple(
            Span(locator=f"line {i}", text=line) for i, line in enumerate(lines, 1) if line.strip()
        ),
        limitation="Model-authored analytical handoff, not a new issuer source or runtime receipt.",
    )
    facts: list[Fact] = []
    tables: list[ReportTable] = []
    key_risks: list[str] = []

    def add(  # noqa: PLR0913 - pre-existing signature (6 arguments at base)
        table_id: str,
        title: str,
        headers: list[str],
        rows: list[tuple[int, str, list[str]]],
        *,
        prose: bool = False,
        company: bool = False,
    ) -> None:
        columns = ["Content"] if prose else headers[1:]
        layouts = []
        for n, (line, quote, values) in enumerate(rows):
            row_id = "company" if company else f"r{n}"
            label = plain(values[0])
            content = (
                ["; ".join(f"{plain(k)}: {plain(v)}" for k, v in zip(headers, values, strict=True))]
                if prose
                else values[1:]
            )
            ids = []
            for c, value in enumerate(content):
                cell_text = plain(value)
                fact_id = f"{table_id}.{row_id}.c{c}"
                ids.append(fact_id)
                facts.append(
                    Fact(
                        fact_id=fact_id,
                        label=label,
                        table_id=table_id,
                        row_id=row_id,
                        field=f"c{c}",
                        text=cell_text or None,
                        status="known" if cell_text else "missing",
                        limitation=None
                        if cell_text
                        else "Original handoff cell is blank; not zero",
                        value_class="source",
                        basis=(
                            "Literal content of the model-authored handoff; "
                            "no new analysis or arithmetic."
                        ),
                        citations=(
                            Citation(
                                source_id=source_id,
                                source_sha256=sha,
                                locator=f"line {line}",
                                quote=quote,
                            ),
                        ),
                    )
                )
            layouts.append(TableRow(row_id=row_id, label=label, fact_ids=tuple(ids)))
        tables.append(
            ReportTable(
                table_id=table_id,
                title=title,
                columns=tuple(
                    TableColumn(field=f"c{c}", label=plain(name)) for c, name in enumerate(columns)
                ),
                rows=tuple(layouts),
                row_header=plain(headers[0]),
            )
        )

    def prose_rows(prefix: str, table_id: str, title: str) -> None:
        found = [(i, line) for i, line in enumerate(lines, 1) if line.startswith(prefix)]
        if len(found) != 1:
            raise ValueError(f"{module_id}: expected one {prefix}")
        i, line = found[0]
        add(table_id, title, ["Item", "Text"], [(i, line, [title, line])])

    if module_id == "CP-1":
        headers, rows = table(section(lines, "T4.10 — Source-supported dashboard"))
        add(
            "evidence-trace",
            "Historical dashboard — USD millions; qualifications retained",
            headers,
            rows,
        )
        gap_id = "T4.12"
    elif module_id == "CP-1A":
        headers, rows = table(section(lines, "Company, business and revenue model"))

        # Live handoffs may prefix these labels with stable evidence-row IDs.
        # Normalize only selection; add() retains the literal label and source line.
        def business_label(row: tuple[int, str, list[str]]) -> str:
            return re.sub(r"^C\d+\s+", "", plain(row[2][0]))

        company_rows = [r for r in rows if business_label(r) == "Company description"]
        if len(company_rows) != 1:
            raise ValueError("CP-1A: expected the company-description row")
        add("company_description", "Company", headers, company_rows, company=True)
        mix_names = {
            "Product mix",
            "Revenue-channel estimate",
            "Aftermarket margin/stability characterization",
            "End markets / concentration",
        }
        add(
            "revenue_business_mix",
            "Revenue and business mix",
            headers,
            [r for r in rows if business_label(r) in mix_names],
        )
        add(
            "operating_model",
            "Operating model",
            headers,
            [r for r in rows if business_label(r) not in mix_names | {"Company description"}],
        )
        for heading, table_id, prose in (
            ("Ownership and control", "ownership_register", False),
            ("Transaction and capital allocation summary", "transaction_summary", True),
            ("Timeline and governance behavior (absorbed CP-2C)", "events_timeline", True),
        ):
            headers, rows = table(section(lines, heading))
            add(table_id, heading, headers, rows, prose=prose)
        gap_id = "gaps_ledger"
    else:
        for prefix, table_id, title in (
            ("**Assessment —", "cp2.key_findings", "Fundamental assessment"),
            ("**Thesis —", "cp2.thesis", "Thesis"),
        ):
            prose_rows(prefix, table_id, title)
        ranked = section(lines, "Ranked strengths, weaknesses and key risks")
        direction = ""
        groups: dict[str, list[tuple[int, str, list[str]]]] = {"Strengths": [], "Weaknesses": []}
        for i, line in ranked:
            if line in {"**Strengths**", "**Weaknesses**"}:
                direction = plain(line)
            elif re.match(r"\d+\. ", line) and direction:
                groups[direction].append((i, line, [direction, re.sub(r"^\d+\. ", "", line)]))
        for name, rows in groups.items():
            if not rows:
                raise ValueError(f"CP-2: missing ranked {name}")
            add(f"cp2.{name.lower()}", name, ["Item", "Text"], rows)
        # The shipped CP-2 bindings hold strengths and weaknesses only; the rated key-risk line
        # is kept literally among the module's limitations rather than dropped.
        key_risks = [plain(line) for _, line in ranked if line.startswith("**Key risks")]
        gap_id = "T2.12"
    headers, gaps = table(section(lines, "Gaps"))
    add(gap_id, "Gaps and restrictions from the handoff", headers, gaps)
    descriptor = next(m for m in modules() if m.module_id == module_id)
    return ModuleView(
        module_id=module_id,
        title=descriptor.title,
        aliases=descriptor.aliases,
        status="candidate",
        artifact_sha256=sha,
        facts=tuple(facts),
        tables=tuple(tables),
        limitations=(
            source.limitation or "",
            *tuple(plain("; ".join(values)) for _, _, values in gaps),
            *key_risks,
        ),
    ), source


def prepare(manifest: Path) -> tuple[View, ReportView, dict[str, bytes]]:
    request = DeliveryRequest.model_validate_json(manifest.read_bytes())
    if set(request.handoffs) != {"CP-1", "CP-1A", "CP-2"}:
        raise ValueError("This adapter requires CP-1, CP-1A and CP-2 handoffs")
    if (
        request.run.pathway != "credit_snapshot"
        or request.run.requested_modules != PUBLIC_S1A_MODULES
        or request.run.case_kind != "public"
    ):
        raise ValueError("This adapter supports only the public five-section snapshot")
    module_views = []
    sources = []
    copies = {}
    for module_id, spec in request.handoffs.items():
        raw = (manifest.parent / spec.path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != spec.sha256:
            raise ValueError(f"Changed handoff: {module_id}")
        if not names_issuer(raw.decode(), (request.run.issuer_name,)):
            raise ValueError(f"Issuer name is not established in {module_id}")
        module, source = mapped_module(module_id, raw)
        module_views.append(module)
        sources.append(source)
        copies[f"{module_id}.md"] = raw
    if request.model is None:
        module_views.append(
            ModuleView(
                module_id="CP-MODEL",
                title="Model publication",
                aliases=(),
                status="blocked",
                limitations=(
                    (
                        "CP-MODEL HTML/chart/calculation-JSON publication has not run. "
                        "This narrative snapshot does not replace it."
                    ),
                ),
            )
        )
        maps = SHIPPED_MAPS
    else:
        from deploy_workflow.model_handoff_delivery import build_model

        if set(request.model.extra_handoffs) - {"quarter", "forecast"}:
            raise ValueError("model_inputs: unknown extra handoff role")
        inputs = {
            "annual": request.handoffs["CP-1"],
            "current_synthesis": request.handoffs["CP-2"],
            **request.model.extra_handoffs,
        }
        if request.model.forecast_exact is not None:
            inputs["forecast_exact"] = request.model.forecast_exact
        raw_inputs = {
            key: (manifest.parent / spec.path).read_bytes() for key, spec in inputs.items()
        }
        publication = build_model(request.run, inputs, raw_inputs, request.model)
        module_views.append(publication.module)
        sources.extend(publication.sources)
        copies.update(publication.files)
        maps = tuple(m for m in SHIPPED_MAPS if m.module_id != "CP-MODEL") + (
            BindingMap(
                module_id="CP-MODEL",
                entries=tuple(
                    Binding(
                        fact_coord=FactCoord(module_id="CP-MODEL", table_id=t.table_id),
                        block_id="evidence",
                        cell_slot="model-" + t.table_id,
                        unit_class="text",
                    )
                    for t in publication.module.tables
                ),
            ),
        )
    view = View(
        run=request.run, mode="candidate", modules=tuple(module_views), sources=tuple(sources)
    )
    preset = next(p for p in pathways() if p.id == "credit_snapshot")
    pathway = preset.model_copy(
        update={"blocks": SECTIONS, "requested_modules": PUBLIC_S1A_MODULES}
    )
    report = build(view, pathway, maps)
    if any(block.state not in {"populated", "collapsed"} for block in report.blocks):
        raise ValueError("The five requested sections must contain actual handoff content")
    return view, report, copies


def delivery_files(manifest: Path) -> dict[str, bytes]:
    """Build the exact publication bytes without writing or executing analysis."""
    request = DeliveryRequest.model_validate_json(manifest.read_bytes())
    if request.layout is not None:
        from deploy_workflow.markdown_delivery import markdown_files

        return markdown_files(request, manifest.parent)
    view, report, copies = prepare(manifest)
    has_model = "model.html" in copies
    rendered = render(view, report)
    anchor = '<div id="call-root"></div>'
    if rendered.count(anchor) != 1:
        raise ValueError("Existing renderer scope-banner location changed")
    banner = (
        '<section id="delivery-scope-banner" class="banner" role="note">'
        + html.escape((MODEL_SCOPE if has_model else SCOPE).format(as_of=view.run.as_of))
        + "</section>"
    )
    if has_model:
        nav = '["model", "Model", "#CP-1"]'
        if rendered.count(nav) != 1:
            raise ValueError("model_shell: main report Model destination changed")
        rendered = rendered.replace(nav, '["model", "Model", "model.html"]')
        banner += '<nav aria-label="Published deliverables"><a href="model.html">HTML Model and charts</a> · <a href="calculation.json">Calculation JSON</a></nav>'
    files = {
        **copies,
        "view.json": view.model_dump_json(indent=2).encode(),
        "report-view.json": report.model_dump_json(indent=2).encode(),
        "report.html": rendered.replace(anchor, banner + anchor).encode(),
    }
    record = {
        "kind": "manual_handoff_delivery",
        "scope": (*SECTIONS, "HTML Model", "charts", "calculation JSON") if has_model else SECTIONS,
        "analytical_runtime_executed": False,
        "cp_model_published": has_model,
        "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
    }
    files["delivery.json"] = (json.dumps(record, indent=2) + "\n").encode()
    return files


def verify_files(destination: Path, expected: dict[str, bytes]) -> Path:
    """Check an exact flat publication, including its receipt, without repairing it."""
    if {p.name for p in destination.iterdir()} != set(expected):
        raise ValueError("delivery_files: publication file set differs")
    for name, raw in expected.items():
        if (destination / name).read_bytes() != raw:
            raise ValueError(f"delivery_changed: {name}")
    return destination / "report.html"


def verify_delivery(manifest: Path, destination: Path) -> Path:
    """Reconstruct and compare every requested file, including the completion record."""
    return verify_files(destination, delivery_files(manifest))


def comparison_files(run: Run, response: bytes, inputs: dict[str, str]) -> dict[str, bytes]:
    """Publish the checked CP-8 answer; input hashes retain prior/current lineage."""
    response_sha = hashlib.sha256(response).hexdigest()
    from deploy_vii.report_view import _refs_by_fact, _slot
    from deploy_workflow.model_handoff_delivery import _literal_tables

    source, facts, tables, _ = _literal_tables("CP-8", response, response_sha)
    titles: dict[str | None, str] = {
        "Bundle": "Selected prior and current publications",
        "Dimension": "Seven requested comparison dimensions",
        "Section": "All five narrative sections",
        "Restriction": "Continuing limitations",
    }
    tables = [t.model_copy(update={"title": titles.get(t.row_header, t.title)}) for t in tables]
    comparisons = [t for t in tables if t.row_header == "Dimension"]
    if (
        len(comparisons) != 1
        or len(comparisons[0].rows) != 7
        or {row.label for row in comparisons[0].rows}
        != {
            "Values",
            "Periods",
            "Assumptions",
            "Conclusions",
            "Sources",
            "Limitations",
            "Output scope",
        }
    ):
        raise ValueError(
            "cp8_dimensions: one comparison table must cover the seven requested dimensions"
        )
    if len(comparisons[0].columns) < 2 or any(
        f.status != "known" for f in facts if f.table_id == comparisons[0].table_id
    ):
        raise ValueError("cp8_dimensions: explain both sides, including explicit absence or gaps")
    module = ModuleView(
        module_id="CP-8",
        title="Run deliverable comparison",
        aliases=(),
        status="candidate",
        artifact_sha256=response_sha,
        facts=tuple(facts),
        tables=tuple(tables),
        limitations=(
            "Checked deliverable comparison, not investment-decision calibration or fresh issuer underwriting.",
        ),
    )
    view = View(
        run=run,
        mode="candidate",
        modules=(module,),
        sources=(source,),
        analytical_qualification="partial",
        native_host_qualification="unrun",
    )
    pathway = next(p for p in pathways() if p.id == run.pathway).model_copy(
        update={
            "title": "Run deliverable comparison",
            "question": "What changed between the prior and current deliverables?",
            "requested_modules": ("CP-8",),
            "blocks": ("what-changed",),
        }
    )
    entries = tuple(
        Binding(
            fact_coord=FactCoord(module_id="CP-8", table_id=t.table_id),
            block_id="what-changed" if t == comparisons[0] else "evidence",
            cell_slot=t.table_id,
            unit_class="text",
        )
        for t in tables
    )
    report = build(view, pathway, (BindingMap(module_id="CP-8", entries=entries),))
    primary = _slot(
        next(e for e in entries if e.block_id == "what-changed"),
        module,
        _refs_by_fact(report.index),
    )
    report = ReportView.model_validate_json(
        report.model_copy(
            update={
                "blocks": tuple(
                    b.model_copy(
                        update={
                            "kind": "dense",
                            "lines": (),
                            "rows": primary.rows,
                            "columns": primary.columns,
                            "row_header": primary.row_header,
                            "title": "Changes across the seven requested dimensions",
                            "owner": "CP-8",
                            "full_analysis_route": "CP-8",
                            "width": "full",
                        }
                    )
                    for b in report.blocks
                )
            }
        ).model_dump_json()
    )
    if any(b.state not in {"populated", "collapsed"} for b in report.blocks):
        raise ValueError("cp8_delivery: comparison must contain actual checked content")
    rendered = render(view, report)
    anchor = '<div id="call-root"></div>'
    if rendered.count(anchor) != 1:
        raise ValueError("Existing renderer scope-banner location changed")
    scope = (
        "Comparison of the explicitly selected prior and current delivery bundles. "
        "Latest local publication does not imply current issuer evidence. "
        "No decision history, returns, new issuer analysis or Excel output. "
        "Limitations and exact source bindings remain in the CP-8 handoff."
    )
    files = {
        "CP-8.md": response,
        "view.json": view.model_dump_json(indent=2).encode(),
        "report-view.json": report.model_dump_json(indent=2).encode(),
        "report.html": rendered.replace(
            anchor,
            '<section id="delivery-scope-banner" class="banner" role="note">'
            + html.escape(scope)
            + "</section>"
            + anchor,
        ).encode(),
        "comparison-inputs.json": (json.dumps(inputs, sort_keys=True, indent=2) + "\n").encode(),
    }
    receipt = {
        "kind": "checked_deliverable_comparison",
        "scope": scope,
        "analytical_runtime_executed": False,
        "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
    }
    files["delivery.json"] = (json.dumps(receipt, indent=2) + "\n").encode()
    return files


def deliver(manifest: Path, destination: Path) -> Path:
    files = delivery_files(manifest)
    destination.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        (destination / name).write_bytes(raw)
    return destination / "report.html"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(deliver(args.manifest, args.output))


if __name__ == "__main__":
    main()
