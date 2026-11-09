"""Publish the checked annual CP-1 layout with the existing Model/chart components.

Promoted from the retained TDG Model builder. Source selectors are explicit data;
the reviewed Decimal helpers still own all calculations. Other handoffs are copied
literally, without annualization or a second analytical execution.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections.abc import Mapping
from datetime import date, timedelta
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
from deploy_vii.model.periods import LTM_DAYS
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
    HEADINGS,
    SOURCE_NUMBER,
    DerivedRows,
    HandoffInput,
    ModelDelivery,
    heading_of,
    hide_comments,
    hide_fenced,
    is_gap,
    names_issuer,
    physical_lines,
    plain,
    table,
    table_row,
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
DERIVED_FORMULAS = {
    "revenue_growth": "revenue / prior-year revenue - 1",
    "gross_margin": "gross_profit / revenue",
    "adj_ebitda_margin": "issuer_as_defined / revenue",
    "adj_ebitda_growth": "issuer_as_defined / prior-year issuer_as_defined - 1",
    "senior_secured_debt": "carrying values of the securitization, the term loans aggregate "
    "and the secured notes at the register date",
    "senior_secured_multiple": "senior_secured_debt / issuer_as_defined",
}
DERIVED_KEYS = tuple(DERIVED_FORMULAS)
DERIVED_UNITS = {
    "senior_secured_debt": "MILLIONS",
    "senior_secured_multiple": "MULTIPLE",
    "ltm_adj_ebitda": "MILLIONS",
    **dict.fromkeys(DERIVED_KEYS[:4], "FRACTION"),
}
QUARTER_FORMULAS = {
    "ltm_adj_ebitda": "fiscal-year Adj EBITDA As Defined + year-to-date window - prior-year window",
    "senior_secured_debt": "Net carrying values of the securitization, the term loans and the "
    "secured notes at the quarter-end register date",
    "senior_secured_multiple": "senior_secured_debt / ltm_adj_ebitda",
}
FORMULAS = {
    "opex_magnitude": "selling_admin + income_statement_amortization",
    "ebit": "gross_profit - opex_magnitude",
    "cash_flow_DA": "depreciation + cf_amortization",
    "operating_ebitda": "ebit + cash_flow_DA",
    "cfo_less_capex": "cfo + capex_signed",
    "carrying_debt": "BS long-term debt + current portion + separate securitization",
    "net_carrying_debt": "carrying_debt - cash",
    "issuer_bridge_check": "issuer ordinary EBITDA + acquisition/integration + stock/deferred compensation + refinancing + other net",
    "operating_vs_issuer_basis": "operating_ebitda - issuer_ordinary_ebitda",
    **{key: f"{num} / {den}" for key, num, den in RATIOS},
}
LABELS = {
    "opex_magnitude": "OPEX below gross profit — S&A plus IS intangible amortization",
    "operating_ebitda": "Operating EBIT plus cash-flow D&A — distinct basis",
    "issuer_ordinary_ebitda": "Issuer ordinary EBITDA — retained reported bridge",
    "issuer_as_defined": "Issuer EBITDA As Defined — management measure",
    "issuer_bridge_check": "Sum of issuer ordinary base and its own adjustments",
    "operating_vs_issuer_basis": "Operating-based less issuer ordinary EBITDA — definition difference",
    "cfo_less_capex": "Reported CFO less gross cash capex — cash proxy only",
    "carrying_debt": "BS carrying borrowing categories plus separate securitization",
    "net_carrying_debt": "Mechanical carrying debt less reported cash — access unverified",
    "cash_flow_DA": "Cash-flow depreciation plus intangible/product-certification amortization",
    "gross_carrying_multiple": "Carrying borrowing / issuer EBITDA As Defined",
    "net_carrying_multiple": "Mechanical net carrying borrowing / issuer EBITDA As Defined",
    "issuer_earnings_cash_interest": "Issuer EBITDA As Defined / reported cash interest",
    "revenue_growth": "Revenue YoY growth",
    "gross_margin": "Gross profit margin",
    "adj_ebitda_margin": "Adj EBITDA margin (As Defined / revenue)",
    "adj_ebitda_growth": "Adj EBITDA YoY growth (As Defined)",
    "senior_secured_debt": "Senior secured carrying debt at the register date",
    "senior_secured_multiple": (
        "Senior secured leverage (secured carrying debt / Adj EBITDA As Defined)"
    ),
    "ltm_adj_ebitda": "LTM Adj EBITDA As Defined at the quarter end",
}


DEFAULT_TABLE_TITLE = "Retained handoff table"
BOLD_LABEL = re.compile(r"\*\*[^*]+\*\*:?")


class ModelPublication(NamedTuple):
    module: ModuleView
    sources: tuple[Source, ...]
    files: dict[str, bytes]


class _NoTable(ValueError):
    """The anchor has no table before the next Markdown heading."""

    def __init__(self, anchor: str) -> None:
        self.note = f"no table under {anchor}"
        super().__init__(f"model_table: {self.note}")


CODE_SPAN = re.compile(r"(`+).+?\1")
FENCE_LINE = re.compile(r"[ \t]*(?:`{3,}|~{3,})")
HEADING_START = re.compile(r" {0,3}(#{1,6})(?:[ \t]|$)")


def _inline_comments(line: str) -> tuple[str, bool]:
    """`line` without its complete HTML comments, and whether one is still open at its end.
    Code spans are blanked before looking for `<!--`; `<!-->` and `<!--->` are whole comments."""
    kept = ""
    while True:
        masked = CODE_SPAN.sub(lambda m: "x" * len(m[0]), line)
        opener = masked.find("<!--")
        if opener < 0:
            return kept + line, False
        if masked.startswith(">", opener + 4):
            end = opener + 5
        elif masked.startswith("->", opener + 4):
            end = opener + 6
        elif (closer := masked.find("-->", opener + 4)) >= 0:
            end = closer + 3
        else:
            return kept + line[:opener], True
        kept, line = kept + line[:opener], line[end:]


def _shown(lines: list[str], source: str) -> list[str]:
    """The lines as a Markdown viewer shows them: comments removed, fenced code blanked. Lines
    are not removed, so numbers hold. A comment never closed would hide the rest: refused."""
    shown, fenced, opened = [], False, False
    for line in lines:
        if opened:
            end = line.find("-->")
            text, opened = ("", True) if end < 0 else _inline_comments(line[end + 3 :])
            shown.append(text)
            continue
        found = HEADING_START.match(line)
        fenced = fenced and not (found and len(found[1]) == 2)
        toggled = FENCE_LINE.match(line) is not None
        fenced ^= toggled
        if fenced or toggled:
            shown.append("")
            continue
        text, opened = _inline_comments(line)
        shown.append(text)
    if opened:
        raise ValueError(f"{source}: an HTML comment is never closed by -->")
    return shown


SEPARATOR = re.compile(r"[ \t]*(?=[^-]*-)(?=.*\|)[ \t:|-]+")
SETEXT = re.compile(r" {0,3}(?:=+|-+)[ \t]*")


def _starts_section(shown: list[str], i: int) -> bool:
    """An ATX heading line, or a text line that is not a table row, underlined by `=` or `-`."""
    if HEADING_START.match(shown[i]):
        return True
    underlined = SETEXT.fullmatch("".join(shown[i + 1 : i + 2])) is not None
    return underlined and bool(shown[i].strip()) and table_row(shown[i]) is None


def _table_at(
    lines: list[str], anchor: str, source: str
) -> tuple[list[str], list[tuple[int, str, list[str]]]]:
    """The table under `anchor` that begins before the next heading, read as shown. Hidden text
    among its rows, or `|` text outside code after them before the next `#` heading that starts
    no table with its own separator row, means rows may be lost: refused (the store's rule)."""
    shown = _shown(lines, source)
    positions = [i for i, line in enumerate(shown) if line == anchor]
    if len(positions) != 1:
        raise ValueError(f"model_anchor: expected one {anchor}")
    start = positions[0] + 1
    end = next((i for i in range(start, len(shown)) if _starts_section(shown, i)), len(shown))
    first = next((i for i in range(start, end) if table_row(shown[i]) is not None), None)
    if first is None:
        raise _NoTable(anchor)
    last = first + 1
    while last < end and table_row(lines[last]) is not None:
        last += 1
    if any(shown[i] != lines[i] for i in range(first, last)):
        raise ValueError(f"model_table: hidden text interrupts the table under {anchor}")
    stop = next((i for i in range(last, len(shown)) if HEADING_START.match(shown[i])), len(shown))
    more = next((i for i in range(last, stop) if "|" in CODE_SPAN.sub("", shown[i])), stop)
    if more < stop and not SEPARATOR.fullmatch("".join(shown[more + 1 : more + 2])):
        raise ValueError(
            f"model_table: the table under {anchor} is split by a blank line or hidden text"
        )
    headers, rows = table([(i + 1, shown[i]) for i in range(first, last)])
    if len(headers) != len(set(headers)):
        raise ValueError("model_columns: selected source columns are ambiguous")
    return headers, rows


class _AnnualReader:
    def __init__(self, raw: bytes, spec: HandoffInput, layout: ModelDelivery) -> None:
        self.lines = physical_lines(raw.decode("utf-8"))
        self.spec, self.layout = spec, layout
        self.citations: dict[str, Citation] = {}

    def selected(self, name: str) -> tuple[list[str], list[tuple[int, str, list[str]]]]:
        return self.table_at(self.layout.anchors[name])

    def table_at(self, anchor: str) -> tuple[list[str], list[tuple[int, str, list[str]]]]:
        return _table_at(self.lines, anchor, "annual")

    def validate(self) -> None:
        required = set(INPUT_KEYS + DEBT_KEYS + ADJUSTMENT_KEYS)
        if set(self.layout.rows) != required:
            raise ValueError("model_rows: selected monetary row meanings must be explicit")
        if set(self.layout.anchors) != {
            "income",
            "cash",
            "balance",
            "dashboard",
            "issuer_bridge",
            "periods",
            "normalization",
        }:
            raise ValueError("model_anchors: the selected CP-1 layout requires seven named tables")
        if any(row.table not in self.layout.anchors for row in self.layout.rows.values()):
            raise ValueError("model_rows: unknown source table")
        for row in self.layout.rows.values():
            if re.search(
                r"\bper\s+(?:common\s+)?share\b|usd\s*/\s*share|\bmillions?\s+(?:of\s+)?shares\b|\(\s*individual\b",
                row.label.casefold(),
            ):
                raise ValueError(
                    "model_quantity_family: selected monetary row has explicit share/per-share units"
                )
        _, normalization = self.selected("normalization")
        normal = [row[2] for row in normalization if row[2][0] == "T4.3 normalization"]
        if len(normal) != 1 or "monetary unit usd millions" not in " ".join(
            plain(normal[0][1]).casefold().split()
        ):
            raise ValueError("model_units: this selected layout requires explicit USD millions")
        headers, rows = self.selected("periods")
        balance_headers, _ = self.selected("balance")
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
            if period.balance_column is not None:
                instants = [row[2] for row in rows if row[2][0] == period.balance_column]
                if (
                    period.balance_column not in balance_headers
                    or len(instants) != 1
                    or instants[0][headers.index("Type")] != "Period end"
                    or instants[0][headers.index("End")] != period.end_date.isoformat()
                ):
                    raise ValueError(f"model_balance_period: source instant differs for {label}")

    def read(self, key: str, column: str | None) -> Cell:
        if column is None:
            return Cell(
                None, "NOT_SOURCED", note="Balance-sheet observation not selected for this period"
            )
        selector = self.layout.rows[key]
        headers, rows = self.selected(selector.table)
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
        if is_gap(lexeme):
            return Cell(
                None, "NOT_STATED", sources=(ref,), note="Source missing/dash retained, never zero"
            )
        if not SOURCE_NUMBER.fullmatch(lexeme):
            raise ValueError(f"model_number: unsupported source spelling {lexeme}")
        value = Decimal(lexeme.replace(",", "").replace("(", "-").replace(")", ""))
        if not value.is_finite():
            raise ValueError("model_number: nonfinite input")
        return Cell(value, basis="REPORTED", sources=(ref,))


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


# The debt register is read as store.secured_debt reads it (apps/issuer-library/engine/store.py);
# the labels are that module's CASHFLOW_LABELS.
SECURITIZATION = "trade receivable securitization"
TERM_LOANS = "term loans aggregate"
SECURED_NOTES = re.compile(r"(?<![a-z])secured notes", re.ASCII)
CARRYING = re.compile(r"carrying\s+(\d[\d,]*(?:\.\d+)?)", re.ASCII)
REGISTER_DATE = re.compile(r"\b([A-Z][a-z]{2}) (\d{1,2}), (\d{4})\b", re.ASCII)
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
UNCLASSIFIED_PHRASE = "the debt register has a row that cannot be classified"
REPEATED_NOTE = "repeated row label: "
REPEATED_PHRASE = "the debt register repeats a row label: "
LABEL_LIMIT = 200
CELL_LIMIT = 4000


class _Register(NamedTuple):
    """The annual debt register: its date and the secured total, or why there is none."""

    when: date | None
    total: Cell


def _register_date(text: str) -> date | None:
    found = REGISTER_DATE.search(text)
    if found is None or found.group(1) not in MONTHS:
        return None
    try:
        return date(int(found.group(3)), MONTHS.index(found.group(1)) + 1, int(found.group(2)))
    except ValueError:
        return None


MARKS = re.compile(r"[*_()]")
TOTAL_AT_EDGE = re.compile(r"(?:(?:sub)?totals?\b.*|.*\b(?:sub)?totals?)")
TOTAL_WORD = re.compile(r"\b(?:sub)?totals?\b")


def _plain(label: str) -> str:
    """A register row label as classified, the store's `plain_label` written again: emphasis marks
    and parentheses removed, whitespace runs one space, trailing `:` and `.` stripped, folded."""
    text = " ".join(MARKS.sub("", label).split())
    return text.rstrip(":.").strip().casefold()


def _total_kind(low: str) -> str | None:
    """`edge` when the whole word total or subtotal starts or ends the plain label (a subtotal),
    `inner` when it sits elsewhere (a row that cannot be classified), else None."""
    if TOTAL_AT_EDGE.fullmatch(low):
        return "edge"
    return "inner" if TOTAL_WORD.search(low) else None


def _secured_register(reader: _AnnualReader, anchor: str) -> _Register:
    """Sum the secured carrying values of the register under `anchor`, classified as the store does.

    Total rows are skipped. A row with a carrying value that is neither secured nor named
    unsecured gives no total (UNCLASSIFIED_ROW, noted with its label); so does a repeated label.
    """
    try:
        headers, rows = reader.table_at(anchor)
    except _NoTable as error:
        return _Register(None, Cell(None, "NOT_SOURCED", note=error.note))
    when = _register_date(headers[1])
    if when is None:
        return _Register(None, Cell(None, "NOT_SOURCED", note="Register date not readable"))
    required = {SECURITIZATION, TERM_LOANS}
    parts: list[tuple[Cell, int]] = []
    named: set[str] = set()
    seen: set[str] = set()
    exact: set[str] = set()
    incomplete = False
    repeated: str | None = None
    unclassified: str | None = None
    for number, quote, values in rows:
        label = values[0]
        low = _plain(label)
        kind = _total_kind(low)
        carrying = CARRYING.search(values[1]) if len(values[1]) <= CELL_LIMIT else None
        if low in seen and carrying is not None and repeated is None:
            repeated = label[:LABEL_LIMIT]
        seen.add(low)
        if label in exact:
            continue  # a later row of a label is dropped, as the store does
        exact.add(label)
        if kind == "edge":
            continue
        unsecured = "subordinated" in low or "unsecured" in low
        secured = kind is None and (
            low in required or (SECURED_NOTES.search(low) and not unsecured)
        )
        if not secured:
            if carrying is not None and not unsecured and unclassified is None:
                unclassified = label[:LABEL_LIMIT]
            continue
        if carrying is None:
            incomplete = True
            continue
        locator = f"line {number}"
        reader.citations[locator] = Citation(
            source_id="annual", source_sha256=reader.spec.sha256, locator=locator, quote=quote
        )
        ref = SourceRef("annual", locator, carrying.group(0))
        amount = Decimal(carrying.group(1).replace(",", ""))
        parts.append((Cell(amount, basis="REPORTED", sources=(ref,)), 1))
        named.add(low)
    if repeated is not None:
        return _Register(when, Cell(None, "UNCLASSIFIED_ROW", note=f"{REPEATED_NOTE}{repeated}"))
    if unclassified is not None:
        return _Register(when, Cell(None, "UNCLASSIFIED_ROW", note=unclassified))
    if incomplete or not required <= named:
        return _Register(
            when,
            Cell(None, "COMPONENT_MISSING", note="A required secured row has no carrying value"),
        )
    with localcontext(CONTEXT):
        return _Register(when, calc(parts))


def _growth(this: Cell, prior: Cell) -> Cell:
    """`this / prior - 1`; no prior-year period is PRIOR_PERIOD_MISSING, never zero."""
    # (this - prior) / prior equals this / prior - 1 and is rounded once: subtracting 1 from a
    # 38-digit quotient would lose a digit.
    return _ratio(((this, 1), (prior, -1)), ((prior, 1),))


FULL_YEAR_DAYS = range(357, 374)
FISCAL_LABEL = re.compile(r"FY([0-9]{4})")


def _is_full_year(layout: ModelDelivery, period: str) -> bool:
    dates = layout.periods[period]
    return (dates.end_date - dates.start_date).days + 1 in FULL_YEAR_DAYS


def _prior_growth(
    layout: ModelDelivery, cells: dict[str, dict[str, Cell]], period: str, key: str
) -> Cell:
    """Growth of `key` on the period labelled FY<n-1>, as the store pairs fiscal years."""
    found = FISCAL_LABEL.fullmatch(period)
    prior = f"FY{int(found.group(1)) - 1}" if found else None
    if prior not in layout.periods:
        return Cell(None, "PRIOR_PERIOD_MISSING", note="No selected period ends a year earlier")
    if not (_is_full_year(layout, period) and _is_full_year(layout, prior)):
        return Cell(None, "PRIOR_PERIOD_MISSING", note="the prior period is not a full year")
    return _growth(cells[period][key], cells[prior][key])


def _derived_cells(
    reader: _AnnualReader, cells: dict[str, dict[str, Cell]], derived: DerivedRows
) -> None:
    """Add the fiscal-year growth, margin and senior secured rows to each period's cells."""
    register = (
        _secured_register(reader, derived.debt_register)
        if derived.debt_register is not None
        else None
    )
    for period, row in cells.items():
        with localcontext(CONTEXT):
            row["revenue_growth"] = _prior_growth(reader.layout, cells, period, "revenue")
            row["gross_margin"] = _ratio(((row["gross_profit"], 1),), ((row["revenue"], 1),))
            row["adj_ebitda_margin"] = _ratio(
                ((row["issuer_as_defined"], 1),), ((row["revenue"], 1),)
            )
            row["adj_ebitda_growth"] = _prior_growth(
                reader.layout, cells, period, "issuer_as_defined"
            )
            if register is None:
                continue
            if (
                register.when is not None
                and register.when != reader.layout.periods[period].end_date
            ):
                row["senior_secured_debt"] = Cell(
                    None, "REGISTER_DATE_DIFFERS", note=f"recorded at {register.when.isoformat()}"
                )
            else:
                row["senior_secured_debt"] = register.total
            row["senior_secured_multiple"] = _ratio(
                ((row["senior_secured_debt"], 1),), ((row["issuer_as_defined"], 1),)
            )


# The quarter handoff: LTM Adj EBITDA and quarter-end senior secured leverage per window.
ADJUSTED_EBITDA_LABEL = (
    "Total Company EBITDA As Defined"  # store.CASHFLOW_LABELS["adjusted_ebitda"]
)
WINDOW_HEADER = re.compile(r"(\d{4}-\d{2}-\d{2})[\u2013-](\d{4}-\d{2}-\d{2})")
QUARTER_DATE = re.compile(r"\b([A-Z][a-z]+) (\d{1,2}), (\d{4})\b", re.ASCII)
FULL_MONTHS = tuple(
    ("January", "February", "March", "April", "May", "June")
    + ("July", "August", "September", "October", "November", "December")
)
YEAR_AGO_DAYS = range(365 - 7, 366 + 8)


class _Window(NamedTuple):
    text: str
    start: date
    end: date
    column: int


def _quarter_cell(number: int, cells: list[str], column: int, source: str = "quarter") -> Cell:
    lexeme = cells[column]
    if is_gap(lexeme):
        return Cell(None, "NOT_STATED", note="Source missing/dash retained, never zero")
    if not SOURCE_NUMBER.fullmatch(lexeme):
        raise ValueError(f"model_number: unsupported source spelling {lexeme}")
    value = Decimal(lexeme.replace(",", "").replace("(", "-").replace(")", ""))
    return Cell(value, basis="REPORTED", sources=(SourceRef(source, f"line {number}", lexeme),))


def _long_date(text: str) -> date | None:
    found = QUARTER_DATE.search(text)
    if found is None or found[1] not in FULL_MONTHS:
        return None
    try:
        return date(int(found[3]), FULL_MONTHS.index(found[1]) + 1, int(found[2]))
    except ValueError:
        return None


QUARTER_REQUIRED = ("securitization", "term loans")


def _kind_of(name: str, low: str) -> bool:
    return name in low if name == "securitization" else low.startswith(name)


def _quarter_register(lines: list[str], anchor: str, end: date) -> Cell:
    """Quarter-end senior secured debt from the `Net` column, classified as the annual one is."""
    try:
        headers, rows = _table_at(lines, anchor, "quarter")
    except _NoTable as error:
        return Cell(None, "NOT_SOURCED", note=error.note)
    return _quarter_register_rows(headers, rows, anchor, end)


def _repeated_quarter_label(
    headers: list[str], rows: list[tuple[int, str, list[str]]], net: int
) -> str | None:
    """The first label (as `_plain` reads it, subtotal and `Less:` rows included) that comes
    again with a Net value, as the annual register counts it; a first copy's value is not read."""
    seen: set[str] = set()
    for number, _, values in rows:
        label = values[headers.index("Label")]
        low = _plain(label)
        if label and low in seen and _quarter_cell(number, values, net).value is not None:
            return label[:LABEL_LIMIT]
        seen.add(low)
    return None


def _quarter_register_rows(
    headers: list[str], rows: list[tuple[int, str, list[str]]], anchor: str, end: date
) -> Cell:
    nets = [i for i, h in enumerate(headers) if h.startswith("Net")]
    if len(nets) != 1 or "Label" not in headers:
        raise ValueError("model_columns: the quarter register needs one Net and a Label column")
    net = nets[0]
    when = _long_date(anchor)
    if when is None:
        return Cell(None, "NOT_SOURCED", note="Register date not readable")
    if when != end:
        return Cell(None, "REGISTER_DATE_DIFFERS", note=f"recorded at {when.isoformat()}")
    parts: list[tuple[Cell, int]] = []
    repeated = _repeated_quarter_label(headers, rows, net)
    unclassified: str | None = None
    incomplete = False
    named: set[str] = set()
    for number, _, values in rows:
        label = values[headers.index("Label")]
        low = _plain(label)
        kind = _total_kind(low)
        if not label or kind == "edge" or low.startswith(("less:", "long-term debt")):
            continue
        amount = _quarter_cell(number, values, net)
        unsecured = "subordinated" in low or "unsecured" in low
        secured = (
            not unsecured
            and kind is None
            and ("securitization" in low or low.startswith("term loans") or "secured notes" in low)
        )
        if secured:
            incomplete |= amount.value is None
            parts.append((amount, 1))
            if amount.value is not None:
                named.update(name for name in QUARTER_REQUIRED if _kind_of(name, low))
        elif amount.value is not None and not unsecured and unclassified is None:
            unclassified = label[:LABEL_LIMIT]
    if repeated is not None:
        return Cell(None, "UNCLASSIFIED_ROW", note=f"{REPEATED_NOTE}{repeated}")
    if unclassified is not None:
        return Cell(None, "UNCLASSIFIED_ROW", note=unclassified)
    if incomplete or named != set(QUARTER_REQUIRED):
        return Cell(None, "COMPONENT_MISSING", note="A required secured row has no Net value")
    with localcontext(CONTEXT):
        return calc(parts)


def _annual_adjusted(lines: list[str], year: str) -> Cell:
    """The fiscal year's As Defined total, read from the one annual table holding its row."""
    lines = hide_fenced(hide_comments(lines, "annual"))
    wanted = _plain(ADJUSTED_EBITDA_LABEL)
    holding = [
        i
        for i, line in enumerate(lines)
        if (row := table_row(line)) is not None and _plain(row[1:].split("|")[0]) == wanted
    ]
    if len(holding) != 1:
        return Cell(
            None, "WINDOW_MISSING", note="fiscal-year Adj EBITDA As Defined is not in one row"
        )
    top = holding[0]
    while top > 0 and table_row(lines[top - 1]) is not None:
        top -= 1
    headers, rows = table([(i + 1, lines[i]) for i in range(top, len(lines))])
    found = next(r for r in rows if _plain(r[2][0]) == wanted)
    if year not in headers:
        return Cell(None, "WINDOW_MISSING", note=f"{year} is not a column of that annual table")
    return _quarter_cell(found[0], found[2], headers.index(year), "annual")


def _ltm_cell(annual: Cell, this: Cell, prior: Cell) -> Cell:
    """Fiscal year + this window - the same window a year earlier; no zero stands in."""
    for operand, name in (
        (annual, "fiscal-year Adj EBITDA As Defined"),
        (this, "year-to-date window"),
        (prior, "prior-year window"),
    ):
        if operand.value is None:
            return Cell(None, operand.reason, note=operand.note or f"{name} is missing")
    with localcontext(CONTEXT):
        return calc(((annual, 1), (this, 1), (prior, -1)))


def _quarter_cells(
    layout: ModelDelivery, annual: list[str], quarter: bytes, derived: DerivedRows
) -> dict[_Window, tuple[dict[str, Cell], date | None]]:
    """The LTM and quarter-end rows of every window that starts a fiscal year, each with the
    first day of its twelve months (the day after the prior-year window ends; None without one)."""
    lines = physical_lines(quarter.decode("utf-8"))
    headers, rows = _table_at(lines, str(derived.quarter_bridge), "quarter")
    if "Label" not in headers:
        raise ValueError("model_columns: the quarter bridge needs a Label column")
    wanted = _plain(ADJUSTED_EBITDA_LABEL)
    found_rows = [r for r in rows if _plain(r[2][headers.index("Label")]) == wanted]
    if len(found_rows) != 1:
        raise ValueError(f"model_row: expected one {ADJUSTED_EBITDA_LABEL}")
    row = found_rows[0]
    windows = []
    for column, header in enumerate(headers):
        found = WINDOW_HEADER.fullmatch(header)
        if found:
            windows.append(
                _Window(header, date.fromisoformat(found[1]), date.fromisoformat(found[2]), column)
            )
    if len({(w.start, w.end) for w in windows}) != len(windows):
        raise ValueError("model_columns: the same window appears twice in the bridge")

    def year_before(window: _Window) -> list[_Window]:
        return [
            w
            for w in windows
            if (window.start - w.start).days in YEAR_AGO_DAYS
            and (window.end - w.end).days in YEAR_AGO_DAYS
        ]

    # A column that is another column's prior-year comparative is an operand only.
    comparatives = {w for window in windows for w in year_before(window)}
    result = {}
    for window in windows:
        year = next(
            (
                label
                for label, dates in layout.periods.items()
                if (window.start - dates.end_date).days == 1
            ),
            None,
        )
        if year is None or window in comparatives:
            continue
        dates = layout.periods[year]
        annual_cell = _annual_adjusted(annual, year)
        if not _is_full_year(layout, year):
            annual_cell = Cell(None, "WINDOW_MISSING", note=f"{year} is not a full year")
        priors = year_before(window)
        ltm_start = None
        span = (window.end - priors[0].end).days if len(priors) == 1 else None
        if span is not None and not LTM_DAYS[0] <= span <= LTM_DAYS[1]:
            prior = Cell(
                None,
                "WINDOW_MISSING",
                note=f"the LTM spans {span} days, outside {LTM_DAYS[0]}-{LTM_DAYS[1]}",
            )
        elif len(priors) == 1 and priors[0].start == dates.start_date:
            prior = _quarter_cell(row[0], row[2], priors[0].column)
            ltm_start = priors[0].end + timedelta(days=1)
        else:
            why = (
                "two prior-year windows match"
                if len(priors) > 1
                else "prior-year window does not start with the fiscal year"
                if priors
                else "prior-year window is missing"
            )
            prior = Cell(None, "WINDOW_MISSING", note=why)
        this = _quarter_cell(row[0], row[2], window.column)
        out = {"ltm_adj_ebitda": _ltm_cell(annual_cell, this, prior)}
        if derived.quarter_debt_register is not None:
            debt = _quarter_register(lines, derived.quarter_debt_register, window.end)
            out["senior_secured_debt"] = debt
            with localcontext(CONTEXT):
                out["senior_secured_multiple"] = _ratio(((debt, 1),), ((out["ltm_adj_ebitda"], 1),))
        result[window] = (out, ltm_start)
    return result


# The line under a table header, exactly as the reader applies it (unstripped).
TABLE_SEPARATOR = re.compile(r"\|[ :|\-]+\|")


def _literal_tables(
    key: str, raw: bytes, digest: str
) -> tuple[Source, list[Fact], list[ReportTable], list[Binding]]:
    lines = physical_lines(raw.decode("utf-8"))
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
    # The source keeps every line; tables come from shown ones, outside comments and fences.
    lines = hide_fenced(hide_comments(lines, key))
    facts: list[Fact] = []
    tables: list[ReportTable] = []
    bindings: list[Binding] = []
    i = 0
    heading = DEFAULT_TABLE_TITLE
    while i < len(lines):
        # Every heading line retitles what follows, so a later section never inherits an earlier
        # one's title; a bold line names a table only when the whole line is the label.
        if found := heading_of(lines[i]):
            heading = plain(found[1]) or DEFAULT_TABLE_TITLE
        elif BOLD_LABEL.fullmatch(lines[i].strip()):
            heading = plain(lines[i].strip())
        if not (
            lines[i].startswith("|")
            and i + 1 < len(lines)
            and TABLE_SEPARATOR.fullmatch(lines[i + 1])
        ):
            i += 1
            continue
        headers, rows = table([(j + 1, lines[j]) for j in range(i, len(lines))])
        tid = f"raw-{key}-{len(tables)}"
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
        tables.append(
            ReportTable(
                table_id=tid,
                title=f"{key}: {heading}",
                columns=tuple(
                    TableColumn(field=f"c{j}", label=plain(name))
                    for j, name in enumerate(headers[1:])
                ),
                rows=tuple(layouts),
                row_header=plain(headers[0]),
            )
        )
        bindings.append(
            Binding(
                fact_coord=FactCoord(module_id="CP-MODEL", table_id=tid),
                block_id="evidence",
                cell_slot=tid,
                unit_class="text",
            )
        )
        i = rows[-1][0]
    return source, facts, tables, bindings


def _fact_unit(key: str, ratio_keys: tuple[str, ...]) -> str:
    """The unit a view fact carries: report_view renders decimal_fraction as a percent."""
    unit = _unit_of(key, ratio_keys)
    return "decimal_fraction" if unit == "FRACTION" else unit


def _limitation(cell: Cell) -> str | None:
    if cell.value is not None:
        return cell.note
    if cell.reason == "UNCLASSIFIED_ROW" and cell.note and cell.note.startswith(REPEATED_NOTE):
        return REPEATED_PHRASE + cell.note[len(REPEATED_NOTE) :]
    if cell.reason == "UNCLASSIFIED_ROW":
        return f"{UNCLASSIFIED_PHRASE}: {cell.note}"
    return cell.note or cell.reason or "Missing source input"


def _unit_of(key: str, ratio_keys: tuple[str, ...]) -> str:
    return DERIVED_UNITS.get(key, "MULTIPLE" if key in ratio_keys else "MILLIONS")


def _pure(key: str, ratio_keys: tuple[str, ...]) -> bool:
    """A dimensionless number: a ratio, a multiple or a fraction, never a monetary amount."""
    return _unit_of(key, ratio_keys) != "MILLIONS"


def _written_decimals(cell: Cell) -> int:
    """Places to show a Model amount: the most the source cells it came from were written to."""
    written = (
        len(found[1]) for ref in cell.sources if (found := re.search(r"\.(\d+)", ref.cell_text))
    )
    return min(6, max(written, default=0))


def _ratio_decimals(value: Decimal | None) -> int:
    """Two places, and more only where two would show a nonzero ratio as zero."""
    places = 2
    with localcontext(CONTEXT):
        while value and places < 6 and abs(value) * 2 < Decimal(1).scaleb(-places):
            places += 1
    return places


def _entry(  # noqa: PLR0913 - one value entry, as the store reads it
    key: str,
    cell: Cell,
    ratio_keys: tuple[str, ...],
    formula: str | None,
    period: str,
    start: str | None,
    end: str,
) -> dict[str, object]:
    return {
        "amount": None if cell.value is None else str(cell.value),
        "unit": _unit_of(key, ratio_keys),
        "quantity_family": "dimensionless" if _pure(key, ratio_keys) else "monetary",
        "currency": None if _pure(key, ratio_keys) else "USD",
        "scale": "1" if _pure(key, ratio_keys) else "1000000",
        "period": period,
        "start_date": start,
        "end_date": end,
        "formula": formula,
        "reason": cell.reason,
        "note": cell.note,
        "sources": [
            {"source_id": s.source_id, "locator": s.source_locator, "cell_text": s.cell_text}
            for s in cell.sources
        ],
    }


def _start_of(key: str, window: _Window, ltm_start: date | None) -> str | None:
    """The start date of a quarter entry: the LTM's twelve months, else the window's own."""
    if key == "ltm_adj_ebitda":
        return None if ltm_start is None else ltm_start.isoformat()
    return window.start.isoformat()


def _quarter_entries(
    layout: ModelDelivery,
    inputs: Mapping[str, HandoffInput],
    raw_inputs: Mapping[str, bytes],
    reader: _AnnualReader,
    ratio_keys: tuple[str, ...],
) -> dict[str, dict[str, dict[str, object]]] | None:
    """The `quarters` of calculation.json: only when the layout asks and a quarter is supplied."""
    if layout.derived is None or not layout.derived.quarter_bridge or "quarter" not in inputs:
        return None
    windows = _quarter_cells(layout, reader.lines, raw_inputs["quarter"], layout.derived)
    return {
        window.text: {
            key: _entry(
                key,
                cell,
                ratio_keys,
                QUARTER_FORMULAS.get(key),
                window.text,
                None if key == "senior_secured_debt" else _start_of(key, window, ltm_start),
                window.end.isoformat(),
            )
            for key, cell in row.items()
        }
        for window, (row, ltm_start) in windows.items()
    }


def _published_cells(reader: _AnnualReader) -> dict[str, dict[str, Cell]]:
    cells = _annual_cells(reader)
    if reader.layout.derived is not None:
        _derived_cells(reader, cells, reader.layout.derived)
    return cells


def _table_specs(
    cells: dict[str, dict[str, Cell]], ratio_keys: tuple[str, ...], present: tuple[str, ...]
) -> list[tuple[str, tuple[str, ...], str]]:
    """The (table id, row keys, block) of the history, ratios and, when requested, derived rows."""
    history = tuple(k for k in next(iter(cells.values())) if k not in ratio_keys + present)
    specs = [
        ("history", history, "financials-credit-metrics"),
        ("ratios", ratio_keys, "company-profile"),
    ]
    return specs + [("derived", present, "company-profile")] * bool(present)


def build_model(  # noqa: PLR0912, PLR0915 - pre-existing size (15 branches, 72 statements at base)
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
    sources = []
    facts: list[Fact] = []
    tables: list[ReportTable] = []
    bindings: list[Binding] = []
    copies = {}
    for key, spec in inputs.items():
        raw = raw_inputs[key]
        if hashlib.sha256(raw).hexdigest() != spec.sha256:
            raise ValueError(f"model_input_changed: {key}")
        copies[key + (".json" if key == "forecast_exact" else ".md")] = raw
        if key == "forecast_exact":
            exact = json.loads(raw)
            json.dumps(exact, allow_nan=False)
            consumed = exact.get("consumed", {}) if isinstance(exact, dict) else {}
            if not isinstance(consumed, dict) or inputs["annual"].sha256 not in consumed.values():
                raise ValueError(
                    "model_forecast_basis: exact forecast does not bind this annual handoff"
                )
            continue
        text = raw.decode("utf-8")
        # A quarter/forecast handoff declares its issuer in the title; the others may name it
        # anywhere. A name counts only as whole words.
        declared = key in {"quarter", "forecast"}
        if not names_issuer(
            physical_lines(text)[0] if declared else text,
            (run.issuer_name, run.issuer_id) if declared else (run.issuer_name,),
        ):
            raise ValueError(f"model_issuer: {key}")
        source, raw_facts, raw_tables, raw_bindings = _literal_tables(key, raw, spec.sha256)
        sources.append(source)
        facts.extend(raw_facts)
        tables.extend(raw_tables)
        bindings.extend(raw_bindings)
    reader = _AnnualReader(raw_inputs["annual"], inputs["annual"], layout)
    reader.validate()
    cells = _published_cells(reader)
    ratio_keys = tuple(key for key, _, _ in RATIOS)
    present = tuple(key for key in DERIVED_KEYS if key in next(iter(cells.values())))
    if not any(row[key].value is not None for row in cells.values() for key in INPUT_KEYS):
        raise ValueError("model_empty: no selected historical monetary observations")
    tables_spec = _table_specs(cells, ratio_keys, present)
    formulas = {**FORMULAS, **{key: DERIVED_FORMULAS[key] for key in present}}
    for tid, keys, block in tables_spec:
        layouts = []
        for key in keys:
            ids = []
            for period, row in cells.items():
                cell = row[key]
                fid = f"{tid}.{key}.{period}"
                ids.append(fid)
                quotes = tuple(
                    dict.fromkeys(reader.citations[s.source_locator] for s in cell.sources)
                )
                facts.append(
                    Fact(
                        fact_id=fid,
                        label=LABELS.get(key, key.replace("_", " ").title()),
                        table_id=tid,
                        row_id=key,
                        field=period,
                        amount=cell.value,
                        status="known" if cell.value is not None else "missing",
                        unit=_fact_unit(key, ratio_keys),
                        scale=Decimal(1) if _pure(key, ratio_keys) else Decimal(1000000),
                        currency=None if _pure(key, ratio_keys) else "USD",
                        period=period,
                        basis="Historical handoff publication. "
                        + (
                            "Existing Decimal helper: " + formulas[key]
                            if key in formulas
                            else "Reported source value; exact handoff citation attached."
                        ),
                        value_class="calculated" if key in formulas else "source",
                        formula=formulas.get(key),
                        calculation_id=f"model.{key}.{period}" if key in formulas else None,
                        citations=quotes,
                        limitation=_limitation(cell),
                        decimals=_ratio_decimals(cell.value)
                        if _pure(key, ratio_keys)
                        else _written_decimals(cell),
                    )
                )
            layouts.append(
                TableRow(
                    row_id=key,
                    label=LABELS.get(key, key.replace("_", " ").title()),
                    fact_ids=tuple(ids),
                )
            )
        tables.append(
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
        bindings.append(
            Binding(
                fact_coord=FactCoord(module_id="CP-MODEL", table_id=tid),
                block_id=block,
                cell_slot=tid,
                unit_class="multiple" if tid == "ratios" else "amount",
                label=tid,
            )
        )
    values = {
        period: {
            key: _entry(
                key,
                cell,
                ratio_keys,
                formulas.get(key),
                period,
                None
                if key in {"cash", "carrying_debt", "net_carrying_debt", "senior_secured_debt"}
                else layout.periods[period].start_date.isoformat(),
                layout.periods[period].end_date.isoformat(),
            )
            for key, cell in row.items()
        }
        for period, row in cells.items()
    }
    quarters = _quarter_entries(layout, inputs, raw_inputs, reader, ratio_keys)
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
        "formulas": formulas,
        "values": values,
        **({"quarters": quarters} if quarters is not None else {}),
        "forecast_exact_file": "forecast_exact.json" if "forecast_exact" in inputs else None,
        "forecast_exact_sha256": inputs["forecast_exact"].sha256
        if "forecast_exact" in inputs
        else None,
    }
    calcraw = (json.dumps(calculation, indent=2) + "\n").encode()
    module = ModuleView(
        module_id="CP-MODEL",
        title=run.issuer_name + " historical Model and conditional source tables",
        aliases=(),
        status="candidate",
        artifact_sha256=hashlib.sha256(calcraw).hexdigest(),
        facts=tuple(facts),
        tables=tuple(tables),
        limitations=(SCOPE,),
    )
    model_run = run.model_copy(update={"requested_modules": ("CP-MODEL",)})
    view = View(
        run=model_run,
        mode="candidate",
        modules=(module,),
        sources=tuple(sources),
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
    report = build(view, pathway, (BindingMap(module_id="CP-MODEL", entries=tuple(bindings)),))
    refs = {
        (item.coord.module_id, item.coord.fact_id): item.ref_ids
        for item in report.index.facts
        if item.coord.fact_id is not None
    }
    figures = []
    for figid, title, series in (
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
    ):
        figures.append(
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
                    _ChartPoint(name, p, f"history.{key}.{p}")
                    for name, key in series
                    for p in cells
                ),
                placement="above",
                summary=(
                    "Selected annual history; distinct definitions and missing observations "
                    "retained."
                ),
            )
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
                "figures": tuple(figures) if b.block_id == "financials-credit-metrics" else (),
                "state": "populated",
            }
        )
        for b in report.blocks
    )
    report = ReportView.model_validate_json(
        report.model_copy(update={"blocks": blocks}).model_dump_json()
    )
    rendered = render(view, report)
    anchor = '<div id="call-root"></div>'
    model_nav = '["model", "Model", "#CP-1"]'
    if rendered.count(anchor) != 1 or rendered.count(model_nav) != 1:
        raise ValueError("model_shell: publication destinations changed")
    rendered = rendered.replace(
        anchor,
        '<section id="delivery-scope-banner" class="banner" role="note">'
        + html.escape(SCOPE)
        + "</section>"
        + anchor,
    ).replace(model_nav, '["model", "Model", "#CP-MODEL"]')
    files = {
        **copies,
        "calculation.json": calcraw,
        "model-view.json": view.model_dump_json(indent=2).encode(),
        "model-report-view.json": report.model_dump_json(indent=2).encode(),
        "model.html": rendered.encode(),
    }
    return ModelPublication(module, tuple(sources), files)
