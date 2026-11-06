"""Publish the checked annual CP-1 layout with the existing Model/chart components.

Promoted from the retained TDG Model builder. Source selectors are explicit data;
the reviewed Decimal helpers still own all calculations. Other handoffs are copied
literally, without annualization or a second analytical execution.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from decimal import Decimal, localcontext
from typing import NamedTuple

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.contracts import (
    Citation,
    Fact,
    ModuleView,
    ReportTable,
    Run,
    Source,
    Span,
    TableColumn,
    TableRow,
    View,
)
from deploy_vii.model._cells import CONTEXT, calc
from deploy_vii.model.frame import Cell, SourceRef
from deploy_vii.model.metrics import _ratio
from deploy_vii.render import render
from deploy_vii.report_view import (
    FactCoord,
    ReportView,
    _ChartPoint,
    _figure_of_points,
    build,
    pathways,
)
from deploy_workflow.handoff_delivery import (
    EXACT_NUMBER,
    HEADINGS,
    HandoffInput,
    ModelDelivery,
    exact_number,
    fence_blocks,
    heading_text,
    names_issuer,
    plain,
    table,
    token_decimals,
    with_scope_banner,
)

SCOPE = (
    "Model publication from checked Markdown handoffs. Selected annual observations, exact "
    "quarter windows and conditional scenarios remain separate. Source tables are literal; "
    "selected annual values use the existing Decimal helpers. Operating EBIT plus cash-flow "
    "D&A is distinct from issuer ordinary and As Defined EBITDA. Cash after capex is a proxy, "
    "carrying debt is not all claims and reported cash is not certified accessible liquidity. "
    "No analytical rerun, Excel output or native accepted head. Charts show selected annual "
    "history only; retained conditional calculations, when supplied, remain unchanged."
)
INPUT_KEYS = (
    "revenue",
    "cogs",
    "gross_profit",
    "selling_admin",
    "income_statement_amortization",
    "ebit_reported",
    "depreciation",
    "cf_amortization",
    "cfo",
    "capex_signed",
    "cash",
    "interest_cash",
    "tax_cash",
    "issuer_ordinary_ebitda",
    "issuer_as_defined",
)
DEBT_KEYS = ("debt_long_term", "debt_current", "debt_securitization")
ADJUSTMENT_KEYS = (
    "adjustment_acquisition",
    "adjustment_compensation",
    "adjustment_refinancing",
    "adjustment_other",
)
RATIOS = (
    ("gross_carrying_multiple", "carrying_debt", "issuer_as_defined"),
    ("net_carrying_multiple", "net_carrying_debt", "issuer_as_defined"),
    ("issuer_earnings_cash_interest", "issuer_as_defined", "interest_cash"),
)
FORMULAS = {
    "opex_magnitude": "selling_admin + income_statement_amortization",
    "ebit": "gross_profit - opex_magnitude",
    "cash_flow_DA": "depreciation + cf_amortization",
    "operating_ebitda": "ebit + cash_flow_DA",
    "cfo_less_capex": "cfo + capex_signed",
    "carrying_debt": "BS long-term debt + current portion + separate securitization",
    "net_carrying_debt": "carrying_debt - cash",
    "issuer_bridge_check": (
        "issuer ordinary EBITDA + acquisition/integration + stock/deferred compensation "
        "+ refinancing + other net"
    ),
    "operating_vs_issuer_basis": "operating_ebitda - issuer_ordinary_ebitda",
    **{key: f"{num} / {den}" for key, num, den in RATIOS},
}
# A line that is only a bold label, e.g. ``**Net income to EBITDA (PDF 53):**``.
BOLD_LABEL = re.compile(r"\*\*[^*]+\*\*:?")
TABLE_SEPARATOR = re.compile(r"\|[ :|\-]+\|")
SHARE_LABEL = re.compile(
    r"\bper\s+(?:common\s+)?share\b|usd\s*/\s*share|\bmillions?\s+(?:of\s+)?shares\b"
    r"|\(\s*individual\b"
)
ANCHORS = frozenset(
    {"income", "cash", "balance", "dashboard", "issuer_bridge", "periods", "normalization"}
)
SourceTable = tuple[list[str], list[tuple[int, str, list[str]]]]
LABELS = {
    "opex_magnitude": "OPEX below gross profit — S&A plus IS intangible amortization",
    "operating_ebitda": "Operating EBIT plus cash-flow D&A — distinct basis",
    "issuer_ordinary_ebitda": "Issuer ordinary EBITDA — retained reported bridge",
    "issuer_as_defined": "Issuer EBITDA As Defined — management measure",
    "issuer_bridge_check": "Sum of issuer ordinary base and its own adjustments",
    "operating_vs_issuer_basis": (
        "Operating-based less issuer ordinary EBITDA — definition difference"
    ),
    "cfo_less_capex": "Reported CFO less gross cash capex — cash proxy only",
    "carrying_debt": "BS carrying borrowing categories plus separate securitization",
    "net_carrying_debt": "Mechanical carrying debt less reported cash — access unverified",
    "cash_flow_DA": "Cash-flow depreciation plus intangible/product-certification amortization",
    "gross_carrying_multiple": "Carrying borrowing / issuer EBITDA As Defined",
    "net_carrying_multiple": "Mechanical net carrying borrowing / issuer EBITDA As Defined",
    "issuer_earnings_cash_interest": "Issuer EBITDA As Defined / reported cash interest",
}


class ModelPublication(NamedTuple):
    module: ModuleView
    sources: tuple[Source, ...]
    files: dict[str, bytes]


class _AnnualReader:
    def __init__(self, raw: bytes, spec: HandoffInput, layout: ModelDelivery) -> None:
        self.lines = raw.decode("utf-8").splitlines()
        self.blocks = fence_blocks(self.lines)
        self.spec, self.layout = spec, layout
        self.citations: dict[str, Citation] = {}
        self._tables: dict[str, SourceTable | None] = {}

    def _section(self, index: int) -> list[tuple[int, str]]:
        """The anchor's own section: to the next heading of its level or above or, for a bold
        label anchor, to the next heading or bold label. Fenced lines read as blank."""
        anchor = self.lines[index]
        level = len(anchor) - len(anchor.lstrip("#")) if heading_text(anchor) is not None else 7
        end = index + 1
        while end < len(self.lines):
            line = self.lines[end]
            if not self.blocks[end] and (
                (heading_text(line) is not None and len(line) - len(line.lstrip("#")) <= level)
                or (level == 7 and BOLD_LABEL.fullmatch(line.strip()) is not None)
            ):
                break
            end += 1
        return [(i + 1, "" if self.blocks[i] else self.lines[i]) for i in range(index + 1, end)]

    def selected(self, name: str) -> SourceTable | None:
        """The first pipe table in the anchor's own section; None when that section has none."""
        if name not in self._tables:
            anchor = self.layout.anchors[name]
            positions = [i for i, line in enumerate(self.lines) if line == anchor]
            if len(positions) != 1:
                raise ValueError(f"model_anchor: expected one {anchor}")
            rows = self._section(positions[0])
            found = table(rows) if any(text.startswith("|") for _, text in rows) else None
            if found is not None and len(found[0]) != len(set(found[0])):
                raise ValueError("model_columns: selected source columns are ambiguous")
            self._tables[name] = found
        return self._tables[name]

    def required(self, name: str) -> SourceTable:
        found = self.selected(name)
        if found is None:
            raise ValueError(f"model_anchor: no table under {self.layout.anchors[name]}")
        return found

    def validate(self) -> None:
        required = set(INPUT_KEYS + DEBT_KEYS + ADJUSTMENT_KEYS)
        if set(self.layout.rows) != required:
            raise ValueError("model_rows: selected monetary row meanings must be explicit")
        if set(self.layout.anchors) != ANCHORS:
            raise ValueError("model_anchors: the selected CP-1 layout requires seven named tables")
        if any(row.table not in self.layout.anchors for row in self.layout.rows.values()):
            raise ValueError("model_rows: unknown source table")
        if any(SHARE_LABEL.search(row.label.casefold()) for row in self.layout.rows.values()):
            raise ValueError(
                "model_quantity_family: selected monetary row has explicit share/per-share units"
            )
        _, normalization = self.required("normalization")
        normal = [row[2] for row in normalization if row[2][0] == "T4.3 normalization"]
        if len(normal) != 1 or "monetary unit usd millions" not in " ".join(
            plain(normal[0][1]).casefold().split()
        ):
            raise ValueError("model_units: this selected layout requires explicit USD millions")
        self._check_periods()
        self._check_period_columns()

    def _check_periods(self) -> None:
        headers, rows = self.required("periods")
        balance = self.selected("balance")
        previous_end = None
        for label, period in self.layout.periods.items():
            matched = [row[2] for row in rows if row[2][0] == label]
            if len(matched) != 1 or not re.fullmatch(r"FY[0-9]{4}", label):
                raise ValueError(f"model_period: expected one source annual period {label}")
            actual = matched[0]
            if actual[headers.index("Type")] != "Historical duration":
                raise ValueError(f"model_period: {label} is not a historical duration")
            if (actual[headers.index("Start")], actual[headers.index("End")]) != (
                period.start_date.isoformat(),
                period.end_date.isoformat(),
            ):
                raise ValueError(f"model_period: source dates differ for {label}")
            if period.end_date < period.start_date or (
                previous_end is not None and period.start_date <= previous_end
            ):
                raise ValueError("model_period: selected annual windows overlap or are unordered")
            previous_end = period.end_date
            if period.balance_column is None:
                continue
            instants = [row[2] for row in rows if row[2][0] == period.balance_column]
            if (
                (balance is not None and period.balance_column not in balance[0])
                or len(instants) != 1
                or instants[0][headers.index("Type")] != "Period end"
                or instants[0][headers.index("End")] != period.end_date.isoformat()
            ):
                raise ValueError(f"model_balance_period: source instant differs for {label}")

    def _check_period_columns(self) -> None:
        """A selected duration table spells at least one selected period exactly and no period
        another way (``FY2024A``, ``FY 2024``), so a spelling difference is not a source gap."""
        periods = {_squashed(label): label for label in self.layout.periods}
        names = {r.table for key, r in self.layout.rows.items() if key not in DEBT_KEYS}
        for name in sorted(names):
            found = self.selected(name)
            if found is None:
                continue
            headers = found[0][1:]
            variants = [
                h
                for h in headers
                if h not in self.layout.periods
                and (_squashed(h) in periods or _squashed(h)[:-1] in periods)
            ]
            if variants or not set(headers) & set(self.layout.periods):
                raise ValueError(
                    f"model_period_column: {self.layout.anchors[name]} columns {headers} must "
                    f"spell the selected periods {list(self.layout.periods)} exactly"
                )

    def read(self, key: str, column: str | None) -> Cell:
        if column is None:
            return Cell(
                None, "NOT_SOURCED", note="Balance-sheet observation not selected for this period"
            )
        selector = self.layout.rows[key]
        found = self.selected(selector.table)
        if found is None:
            return Cell(
                None,
                "NOT_SOURCED",
                note=f"No table under {self.layout.anchors[selector.table]} in this source",
            )
        headers, rows = found
        matches = [r for r in rows if r[2][0] == selector.label]
        if len(matches) != 1:
            raise ValueError(f"model_row: expected one {selector.label}")
        if column not in headers:
            return Cell(
                None, "NOT_SOURCED", note="Period is absent from this retained source bridge"
            )
        number, quote, values = matches[0]
        lexeme = values[headers.index(column)]
        locator = f"line {number}"
        ref = SourceRef("annual", locator, lexeme)
        self.citations[locator] = Citation(
            source_id="annual", source_sha256=self.spec.sha256, locator=locator, quote=quote
        )
        if lexeme in {"", "—", "Insufficient Information", "Not reconstructed"}:
            return Cell(
                None, "NOT_STATED", sources=(ref,), note="Source missing/dash retained, never zero"
            )
        if not EXACT_NUMBER.fullmatch(lexeme):
            raise ValueError(f"model_number: unsupported source spelling {lexeme}")
        value = exact_number(lexeme)
        if not value.is_finite():
            raise ValueError("model_number: nonfinite input")
        return Cell(value, basis="REPORTED", sources=(ref,))


def _squashed(label: str) -> str:
    return re.sub(r"[^0-9a-z]", "", label.casefold())


def _annual_cells(reader: _AnnualReader) -> dict[str, dict[str, Cell]]:
    """The original checked Model formulas, still calculated by the shared kernel."""
    result = {}
    for period, dates in reader.layout.periods.items():
        c = {key: reader.read(key, period) for key in INPUT_KEYS}
        if c["capex_signed"].value is not None and c["capex_signed"].value > 0:
            raise ValueError(
                "model_capex: select a signed source cash outflow, do not infer its sign"
            )
        with localcontext(CONTEXT):
            c["opex_magnitude"] = calc(
                ((c["selling_admin"], 1), (c["income_statement_amortization"], 1))
            )
            c["ebit"] = calc(((c["gross_profit"], 1), (c["opex_magnitude"], -1)))
            c["cash_flow_DA"] = calc(((c["depreciation"], 1), (c["cf_amortization"], 1)))
            c["operating_ebitda"] = calc(((c["ebit"], 1), (c["cash_flow_DA"], 1)))
            c["cfo_less_capex"] = calc(((c["cfo"], 1), (c["capex_signed"], 1)))
            c["carrying_debt"] = calc(
                (reader.read(key, dates.balance_column), 1) for key in DEBT_KEYS
            )
            c["net_carrying_debt"] = calc(((c["carrying_debt"], 1), (c["cash"], -1)))
            c["issuer_bridge_check"] = calc(
                (
                    (c["issuer_ordinary_ebitda"], 1),
                    *((reader.read(key, period), 1) for key in ADJUSTMENT_KEYS),
                )
            )
            c["operating_vs_issuer_basis"] = calc(
                ((c["operating_ebitda"], 1), (c["issuer_ordinary_ebitda"], -1))
            )
            for key, numerator, denominator in RATIOS:
                c[key] = _ratio(((c[numerator], 1),), ((c[denominator], 1),))
        for computed, stated in (
            ("ebit", "ebit_reported"),
            ("issuer_bridge_check", "issuer_as_defined"),
        ):
            if (
                c[computed].value is not None
                and c[stated].value is not None
                and c[computed].value != c[stated].value
            ):
                raise ValueError(f"model_reconciliation: {period} {computed} differs from {stated}")
        result[period] = c
    return result


def _raw_table(
    key: str, digest: str, tid: str, heading: str, found: SourceTable
) -> tuple[list[Fact], ReportTable]:
    headers, rows = found
    facts: list[Fact] = []
    layouts = []
    for ri, (number, quote, values) in enumerate(rows):
        ids = []
        for ci, text in enumerate(values[1:]):
            fid = f"{tid}.r{ri}.c{ci}"
            ids.append(fid)
            missing = not text.strip()
            facts.append(
                Fact(
                    fact_id=fid,
                    label=plain(values[0]),
                    table_id=tid,
                    row_id=f"r{ri}",
                    field=f"c{ci}",
                    text=None if missing else plain(text),
                    status="missing" if missing else "known",
                    limitation="Original source cell is blank; not zero" if missing else None,
                    basis="Literal handoff table; no financial reinterpretation.",
                    value_class="source",
                    citations=(
                        Citation(
                            source_id=key,
                            source_sha256=digest,
                            locator=f"line {number}",
                            quote=quote,
                        ),
                    ),
                )
            )
        layouts.append(TableRow(row_id=f"r{ri}", label=plain(values[0]), fact_ids=tuple(ids)))
    report_table = ReportTable(
        table_id=tid,
        title=f"{key}: {heading}",
        columns=tuple(
            TableColumn(field=f"c{j}", label=plain(name)) for j, name in enumerate(headers[1:])
        ),
        rows=tuple(layouts),
        row_header=plain(headers[0]),
    )
    return facts, report_table


def _literal_tables(
    key: str, raw: bytes, digest: str
) -> tuple[Source, list[Fact], list[ReportTable], list[Binding]]:
    """Every pipe table of a handoff, cell for cell. A pipe row outside a table is refused, so
    no table is dropped; fenced code is not a table or heading."""
    lines = raw.decode("utf-8").splitlines()
    if tuple(line[3:] for line in lines if line.startswith("## ")) != HEADINGS:
        raise ValueError(f"model_handoff: six ordered headings required in {key}")
    source = Source(
        source_id=key,
        name=key + ".md",
        status="ready",
        sha256=digest,
        media_type="text/markdown",
        spans=tuple(
            Span(locator=f"line {i}", text=line) for i, line in enumerate(lines, 1) if line.strip()
        ),
        extractor="literal-markdown-lines",
        extraction_status="complete",
        limitation="Actual analytical handoff; underlying source qualifications and scope remain.",
    )
    blocks = fence_blocks(lines)
    facts: list[Fact] = []
    tables: list[ReportTable] = []
    i = 0
    heading = "Retained handoff table"
    while i < len(lines):
        line = lines[i]
        if not blocks[i] and (heading_text(line) is not None or BOLD_LABEL.fullmatch(line.strip())):
            heading = plain(line.lstrip("#").strip())
        if blocks[i] or not line.startswith("|"):
            i += 1
            continue
        end = i
        while end < len(lines) and not blocks[end] and lines[end].startswith("|"):
            end += 1
        if end - i < 2 or not TABLE_SEPARATOR.fullmatch(lines[i + 1].rstrip()):
            raise ValueError(
                f"model_handoff: pipe rows outside a table in {key} at line {i + 1}; "
                "give the table a header separator row or remove the pipes"
            )
        tid = f"raw-{key}-{len(tables)}"
        raw_facts, report_table = _raw_table(
            key, digest, tid, heading, table([(j + 1, lines[j]) for j in range(i, end)])
        )
        facts.extend(raw_facts)
        tables.append(report_table)
        i = end
    bindings = [
        Binding(
            fact_coord=FactCoord(module_id="CP-MODEL", table_id=t.table_id),
            block_id="evidence",
            cell_slot=t.table_id,
            unit_class="text",
        )
        for t in tables
    ]
    return source, facts, tables, bindings


class _Literal(NamedTuple):
    sources: list[Source]
    facts: list[Fact]
    tables: list[ReportTable]
    bindings: list[Binding]
    copies: dict[str, bytes]


def _check_forecast(inputs: Mapping[str, HandoffInput], raw: bytes) -> None:
    exact = json.loads(raw)
    json.dumps(exact, allow_nan=False)
    consumed = exact.get("consumed", {}) if isinstance(exact, dict) else {}
    if not isinstance(consumed, dict) or inputs["annual"].sha256 not in consumed.values():
        raise ValueError("model_forecast_basis: exact forecast does not bind this annual handoff")


def _literal_inputs(
    run: Run, inputs: Mapping[str, HandoffInput], raw_inputs: Mapping[str, bytes]
) -> _Literal:
    """Copy every input; each handoff names the issuer (a quarter/forecast in its title)."""
    literal = _Literal([], [], [], [], {})
    for key, spec in inputs.items():
        raw = raw_inputs[key]
        if hashlib.sha256(raw).hexdigest() != spec.sha256:
            raise ValueError(f"model_input_changed: {key}")
        literal.copies[key + (".json" if key == "forecast_exact" else ".md")] = raw
        if key == "forecast_exact":
            _check_forecast(inputs, raw)
            continue
        text = raw.decode("utf-8")
        identified = (
            names_issuer(text.splitlines()[0], (run.issuer_name, run.issuer_id))
            if key in {"quarter", "forecast"}
            else names_issuer(text, (run.issuer_name,))
        )
        if not run.issuer_name.strip() or not identified:
            raise ValueError(f"model_issuer: {key}")
        source, raw_facts, raw_tables, raw_bindings = _literal_tables(key, raw, spec.sha256)
        literal.sources.append(source)
        literal.facts.extend(raw_facts)
        literal.tables.extend(raw_tables)
        literal.bindings.extend(raw_bindings)
    return literal


def _history_decimals(cell: Cell) -> int:
    """Display places of a reported value or sum: those its source spellings carry."""
    return max((token_decimals(s.cell_text, "amount") for s in cell.sources), default=0)


def _register_fact(tid: str, key: str, period: str, cell: Cell, reader: _AnnualReader) -> Fact:
    ratio = tid == "ratios"
    return Fact(
        fact_id=f"{tid}.{key}.{period}",
        label=LABELS.get(key, key.replace("_", " ").title()),
        table_id=tid,
        row_id=key,
        field=period,
        amount=cell.value,
        status="known" if cell.value is not None else "missing",
        unit="MULTIPLE" if ratio else "MILLIONS",
        scale=Decimal(1) if ratio else Decimal(1000000),
        currency=None if ratio else "USD",
        period=period,
        basis="Historical handoff publication. "
        + (
            "Existing Decimal helper: " + FORMULAS[key]
            if key in FORMULAS
            else "Reported source value; exact handoff citation attached."
        ),
        value_class="calculated" if key in FORMULAS else "source",
        formula=FORMULAS.get(key),
        calculation_id=f"model.{key}.{period}" if key in FORMULAS else None,
        citations=tuple(dict.fromkeys(reader.citations[s.source_locator] for s in cell.sources)),
        limitation=cell.note
        if cell.value is not None
        else (cell.note or cell.reason or "Missing source input"),
        decimals=2 if ratio else _history_decimals(cell),
    )


def _register_tables(
    cells: dict[str, dict[str, Cell]], reader: _AnnualReader, literal: _Literal
) -> None:
    ratio_keys = tuple(key for key, _, _ in RATIOS)
    for tid, keys, block in (
        (
            "history",
            tuple(k for k in next(iter(cells.values())) if k not in ratio_keys),
            "financials-credit-metrics",
        ),
        ("ratios", ratio_keys, "company-profile"),
    ):
        layouts = []
        for key in keys:
            ids = []
            for period, row in cells.items():
                literal.facts.append(_register_fact(tid, key, period, row[key], reader))
                ids.append(literal.facts[-1].fact_id)
            layouts.append(
                TableRow(
                    row_id=key,
                    label=LABELS.get(key, key.replace("_", " ").title()),
                    fact_ids=tuple(ids),
                )
            )
        literal.tables.append(
            ReportTable(
                table_id=tid,
                title="Annual source and computation register"
                if tid == "history"
                else "Defined historical ratios — not covenant/agency measures",
                columns=tuple(TableColumn(field=p, label=p) for p in cells),
                rows=tuple(layouts),
                row_header="Measure",
            )
        )
        literal.bindings.append(
            Binding(
                fact_coord=FactCoord(module_id="CP-MODEL", table_id=tid),
                block_id=block,
                cell_slot=tid,
                unit_class="multiple" if tid == "ratios" else "amount",
                label=tid,
            )
        )


def _calculation_record(
    inputs: Mapping[str, HandoffInput], layout: ModelDelivery, cells: dict[str, dict[str, Cell]]
) -> bytes:
    ratio_keys = {key for key, _, _ in RATIOS}
    values = {
        period: {
            key: {
                "amount": None if cell.value is None else str(cell.value),
                "unit": "MULTIPLE" if key in ratio_keys else "MILLIONS",
                "quantity_family": "dimensionless" if key in ratio_keys else "monetary",
                "currency": None if key in ratio_keys else "USD",
                "scale": "1" if key in ratio_keys else "1000000",
                "period": period,
                "start_date": (
                    None
                    if key in {"cash", "carrying_debt", "net_carrying_debt"}
                    else layout.periods[period].start_date.isoformat()
                ),
                "end_date": layout.periods[period].end_date.isoformat(),
                "formula": FORMULAS.get(key),
                "reason": cell.reason,
                "note": cell.note,
                "sources": [
                    {
                        "source_id": s.source_id,
                        "locator": s.source_locator,
                        "cell_text": s.cell_text,
                    }
                    for s in cell.sources
                ],
            }
            for key, cell in row.items()
        }
        for period, row in cells.items()
    }
    calculation = {
        "schema_version": "retained-handoff-model/1",
        "arithmetic_context": {"precision": CONTEXT.prec, "rounding": CONTEXT.rounding},
        "mode": "Separate deterministic publication from checked handoffs",
        "inputs": {
            k: {"path": k + (".json" if k == "forecast_exact" else ".md"), "sha256": v.sha256}
            for k, v in inputs.items()
        },
        "excel_output": False,
        "scope": SCOPE,
        "annual_periods": list(cells),
        "formulas": FORMULAS,
        "values": values,
        "forecast_exact_file": "forecast_exact.json" if "forecast_exact" in inputs else None,
        "forecast_exact_sha256": inputs["forecast_exact"].sha256
        if "forecast_exact" in inputs
        else None,
    }
    return (json.dumps(calculation, indent=2) + "\n").encode()


FIGURES = (
    (
        "M1",
        "Operating and issuer earnings bases",
        (
            ("Operating EBIT plus D&A", "operating_ebitda"),
            ("Issuer ordinary EBITDA", "issuer_ordinary_ebitda"),
            ("Issuer As Defined", "issuer_as_defined"),
        ),
    ),
    (
        "M2",
        "Reported operating cash and capex proxy",
        (("Reported CFO", "cfo"), ("CFO less gross cash capex", "cfo_less_capex")),
    ),
    ("M3", "OPEX below gross profit", (("S&A plus IS amortization", "opex_magnitude"),)),
)


def _model_report(module: ModuleView, report: ReportView, periods: tuple[str, ...]) -> ReportView:
    """The built Model report with the M1-M3 history figures and its block titles."""
    refs = {
        (item.coord.module_id, item.coord.fact_id): item.ref_ids
        for item in report.index.facts
        if item.coord.fact_id is not None
    }
    figures = tuple(
        _figure_of_points(
            "financials-credit-metrics",
            module,
            refs,
            fig_id=figid,
            title=title,
            kind="line",
            unit_class="amount",
            unit="USDm",
            series=tuple(name for name, _ in series),
            points=tuple(
                _ChartPoint(name, p, f"history.{key}.{p}") for name, key in series for p in periods
            ),
            placement="above",
            summary=(
                "Selected annual history; distinct definitions and missing observations retained."
            ),
        )
        for figid, title, series in FIGURES
    )
    blocks = tuple(
        b.model_copy(
            update={
                "owner": "CP-MODEL",
                "title": "Annual financial Model"
                if b.block_id == "financials-credit-metrics"
                else "Defined historical ratios",
                "kind": b.kind if b.block_id == "financials-credit-metrics" else "dense",
                "full_analysis_route": "CP-MODEL",
                "width": "full",
                "figures": figures if b.block_id == "financials-credit-metrics" else (),
                "state": "populated",
            }
        )
        for b in report.blocks
    )
    return ReportView.model_validate_json(
        report.model_copy(update={"blocks": blocks}).model_dump_json()
    )


def build_model(
    run: Run,
    inputs: Mapping[str, HandoffInput],
    raw_inputs: Mapping[str, bytes],
    layout: ModelDelivery,
) -> ModelPublication:
    """Render a current source-bound Model; no providers, journals or output writes."""
    if set(inputs) != set(raw_inputs) or not {"annual", "current_synthesis"} <= set(inputs):
        raise ValueError("model_inputs: annual and current synthesis are required")
    if set(inputs) - {"annual", "current_synthesis", "quarter", "forecast", "forecast_exact"}:
        raise ValueError("model_inputs: unknown source role")
    if ("forecast" in inputs) != ("forecast_exact" in inputs):
        raise ValueError(
            "model_forecast: handoff and unchanged exact calculation must be supplied together"
        )
    literal = _literal_inputs(run, inputs, raw_inputs)
    reader = _AnnualReader(raw_inputs["annual"], inputs["annual"], layout)
    reader.validate()
    cells = _annual_cells(reader)
    if not any(row[key].value is not None for row in cells.values() for key in INPUT_KEYS):
        raise ValueError("model_empty: no selected historical monetary observations")
    _register_tables(cells, reader, literal)
    calcraw = _calculation_record(inputs, layout, cells)
    module = ModuleView(
        module_id="CP-MODEL",
        title=run.issuer_name + " historical Model and conditional source tables",
        aliases=(),
        status="candidate",
        artifact_sha256=hashlib.sha256(calcraw).hexdigest(),
        facts=tuple(literal.facts),
        tables=tuple(literal.tables),
        limitations=(SCOPE,),
    )
    model_run = run.model_copy(update={"requested_modules": ("CP-MODEL",)})
    view = View(
        run=model_run,
        mode="candidate",
        modules=(module,),
        sources=tuple(literal.sources),
        analytical_qualification="partial",
        native_host_qualification="unrun",
    )
    pathway = next(p for p in pathways() if p.id == run.pathway).model_copy(
        update={
            "title": run.issuer_name + " — Model",
            "question": "What do the retained handoffs and explicitly defined calculations show?",
            "requested_modules": ("CP-MODEL",),
            "blocks": ("financials-credit-metrics", "company-profile"),
        }
    )
    built = build(
        view, pathway, (BindingMap(module_id="CP-MODEL", entries=tuple(literal.bindings)),)
    )
    report = _model_report(module, built, tuple(cells))
    rendered = with_scope_banner(render(view, report), SCOPE, model_nav="#CP-MODEL")
    files = {
        **literal.copies,
        "calculation.json": calcraw,
        "model-view.json": view.model_dump_json(indent=2).encode(),
        "model-report-view.json": report.model_dump_json(indent=2).encode(),
        "model.html": rendered.encode(),
    }
    return ModelPublication(module, tuple(literal.sources), files)
