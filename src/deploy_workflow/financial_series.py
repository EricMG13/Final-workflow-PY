"""Source-native chart coordinates from a selected settled CP1 register.

This projection selects facts, never calculates financial values or display text.
Its bounded support is four reported quarters and a complete current facility
snapshot in USD millions, IFRS consolidated group. Authentication belongs to the
unchanged envelope/publication boundary; a ModuleView alone is not that proof.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Literal

from deploy_vii.contracts import Fact, ModuleView
from deploy_workflow.trailing_period import states_trailing_period


@dataclass(frozen=True, slots=True)
class FinancialSeriesPoint:
    series: str
    category: str
    fact_id: str
    companion_fact_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FinancialFigureSeries:
    fig_id: str
    title: str
    kind: Literal["line", "grouped"]
    unit_class: Literal["amount", "multiple"]
    unit: str
    series: tuple[str, ...]
    points: tuple[FinancialSeriesPoint, ...]
    reason: str | None


@dataclass(frozen=True)
class _Period:
    identity: str
    kind: str
    end: date
    row: dict[str, Fact]


_PERIOD_FIELDS = (
    "period_id",
    "period_type",
    "fiscal_year",
    "fiscal_quarter",
    "start_date",
    "end_date",
    "currency",
    "unit",
    "accounting_basis",
    "entity_perimeter",
)
# The T4.14 period types (financial_contracts.FinancialPeriod.period_type) the projection reads,
# and the two it leaves out of the chart periods.
_CHART_KINDS = frozenset({"QUARTER", "FY", "PERIOD_END"})
_UNPLOTTED_KINDS = frozenset({"YTD", "LTM"})
_SERIES = (
    ("S.1", "Leverage", ("total_leverage_reported", "net_leverage_reported")),
    ("S.2", "Interest cover", ("interest_coverage_reported",)),
    ("S.3", "Liquidity", ("cash_closing", "undrawn_rcf", "liquidity")),
    # S.5 reads T4.10 `revenue` and `adjusted_ebitda` (T4.5 is the cash-flow statement).
    ("S.5", "Net revenues and Adjusted EBITDA", ("revenue", "adjusted_ebitda")),
)
_MONEY_FIGURES = frozenset({"S.3", "S.5"})


def _text(fact: Fact) -> str:
    if fact.status != "known" or fact.text is None or fact.amount is not None:
        raise ValueError(f"Unresolved chart identity: {fact.fact_id}")
    return fact.text


def _rows(module: ModuleView, table: str) -> tuple[dict[str, Fact], ...]:
    rows: dict[str, dict[str, Fact]] = {}
    for fact in module.facts:
        if fact.table_id == table:
            if fact.status == "known":
                if (fact.amount is None) == (fact.text is None):
                    raise ValueError(f"Malformed known chart fact: {fact.fact_id}")
            elif fact.amount is not None or fact.text is not None or not fact.limitation:
                raise ValueError(f"Malformed nonknown chart fact: {fact.fact_id}")
            if fact.amount is not None and not fact.amount.is_finite():
                raise ValueError(f"Nonfinite chart fact: {fact.fact_id}")
            row = rows.setdefault(fact.row_id, {})
            if fact.field in row:
                raise ValueError(f"Duplicate chart coordinate: {table}/{fact.row_id}/{fact.field}")
            row[fact.field] = fact
    return tuple(rows.values())


def _periods(module: ModuleView) -> tuple[tuple[_Period, ...], frozenset[str]]:
    """The plotted T4.14 periods by date, and the ids of the YTD and LTM periods left out."""
    periods = []
    unplotted = set()
    seen = set()
    for row in _rows(module, "T4.14"):
        if not set(_PERIOD_FIELDS) <= row.keys():
            raise ValueError("Incomplete T4.14 chart identity")
        identity = _text(row["period_id"])
        if identity in seen or any(f.period != identity for f in row.values()):
            raise ValueError("Ambiguous T4.14 chart period")
        seen.add(identity)
        scope = tuple(
            _text(row[key]) for key in ("currency", "unit", "accounting_basis", "entity_perimeter")
        )
        if scope != ("USD", "MILLIONS", "IFRS", "consolidated group"):
            raise ValueError("Unsupported chart currency, unit or perimeter")
        if any(f.basis != "IFRS · consolidated group" for f in row.values()):
            raise ValueError("Inconsistent chart period perimeter")
        kind = _text(row["period_type"])
        if kind in _UNPLOTTED_KINDS:
            # A YTD or LTM row is a valid register period the charts do not plot (only QUARTER
            # rows are plotted; QUARTER and FY rows give the facility snapshot). It is checked
            # above and left out here, never an exception out of the renderer.
            unplotted.add(identity)
            continue
        if kind not in _CHART_KINDS:
            raise ValueError("Unsupported historical chart period type")
        periods.append(_Period(identity, kind, date.fromisoformat(_text(row["end_date"])), row))
    return tuple(sorted(periods, key=lambda p: (p.end, p.identity))), frozenset(unplotted)


def _basis(identity: str) -> str:
    """Adopted financial_model historical/Q identity, not a label-based join.

    financial_periods._id length-prefixes each part; financial_model._basis_id
    uses ('historical', column_id), and a reported quarter column is Q:<id>.
    Keep this local identity boundary pinned by literal contract tests rather
    than exposing or importing private financial calculation helpers.
    """
    parts = ("historical", f"Q:{identity}")
    raw = "".join(f"{len(part)}:{part}" for part in parts).encode()
    return "model-basis:" + hashlib.sha256(raw).hexdigest()


def _numeric(fact: Fact, money: bool) -> None:
    dimensions = (fact.unit, fact.currency, fact.scale, fact.basis)
    expected = (
        ("MILLIONS", "USD", Decimal(1000000), "IFRS · consolidated group")
        if money
        else ("MULTIPLE", None, Decimal(1), "IFRS · consolidated group")
    )
    if dimensions != expected or fact.text is not None:
        raise ValueError(f"Incompatible chart dimensions: {fact.fact_id}")
    if fact.status == "known":
        if fact.amount is None or not fact.amount.is_finite():
            raise ValueError(f"Nonfinite or absent chart value: {fact.fact_id}")
    elif fact.amount is not None or not fact.limitation:
        raise ValueError(f"Invalid chart gap: {fact.fact_id}")


_QUARTER_SCOPE = (
    "Charts require four contiguous reported QUARTER periods numbered Q1 to Q4 of one fiscal "
    "year; no periods were fabricated."
)


def _quarter_scope(quarters: tuple[_Period, ...]) -> str | None:
    """None for four contiguous quarters Q1 to Q4 of one fiscal year, else the unsupported
    reason (a trailing four quarters across a year end, a gap). Contradictory identities raise:
    a start after its end, quarters that overlap, a quarter number outside 1 to 4, or (fiscal
    year, quarter) labels that repeat or do not increase with the dates."""
    labels = [
        (_text(p.row["fiscal_year"]), _text(p.row["fiscal_quarter"]).removeprefix("Q"))
        for p in quarters
    ]
    if any(n not in {"1", "2", "3", "4"} for _, n in labels) or any(
        a >= b for a, b in pairwise(labels)
    ):
        raise ValueError("Ambiguous QUARTER identities")
    spans = [(date.fromisoformat(_text(p.row["start_date"])), p.end) for p in quarters]
    if any(start > end for start, end in spans) or any(b[0] <= a[1] for a, b in pairwise(spans)):
        raise ValueError("Overlapping or inverted QUARTER periods")
    contiguous = all(b[0] == a[1] + timedelta(days=1) for a, b in pairwise(spans))
    year = labels[0][0]
    if contiguous and labels == [(year, n) for n in ("1", "2", "3", "4")]:
        return None
    return _QUARTER_SCOPE


def _kpi_metrics(module: ModuleView) -> dict[str, dict[str, Fact]]:
    """The T4.10 rows by their `field_1` metric identity; a missing or repeated one raises."""
    metrics: dict[str, dict[str, Fact]] = {}
    for row in _rows(module, "T4.10"):
        if "field_1" not in row:
            raise ValueError("Missing KPI metric identity")
        key = _text(row["field_1"])
        if key in metrics:
            raise ValueError("Duplicate KPI metric identity")
        metrics[key] = row
    return metrics


def _quarter_figures(
    module: ModuleView, periods: tuple[_Period, ...]
) -> tuple[FinancialFigureSeries, ...]:
    quarters = tuple(p for p in periods if p.kind == "QUARTER")
    reason: str | None
    if len(quarters) != 4:
        reason = "Charts require exactly four reported QUARTER periods; no periods were fabricated."
    else:
        reason = _quarter_scope(quarters)
    metrics = _kpi_metrics(module)

    coordinates: list[tuple[str, str, str, str, tuple[str, ...]]] = []
    if reason is None:
        for period in quarters:
            dates = f"{_text(period.row['start_date'])} to {period.end.isoformat()}"
            category = (
                f"Q{_text(period.row['fiscal_quarter']).removeprefix('Q')} "
                f"{_text(period.row['fiscal_year'])}"
            )
            companions = tuple(period.row[k].fact_id for k in _PERIOD_FIELDS)
            coordinates.append(
                (period.identity, _basis(period.identity), dates, category, companions)
            )

    figures = []
    for fig_id, title, series in _SERIES:
        money = fig_id in _MONEY_FIGURES
        points: list[FinancialSeriesPoint] = []
        for key in series:
            if key not in metrics:
                raise ValueError(f"Missing chart metric implementation: {key}")
        if reason is None:
            for key in series:
                metric = metrics[key]
                metric_id = metric["field_1"].fact_id
                for identity, field, dates, category, period_companions in coordinates:
                    if field not in metric:
                        raise ValueError(f"Missing canonical QUARTER basis: {key}/{identity}")
                    fact = metric[field]
                    _numeric(fact, money)
                    if not _states_dates(fact.period, dates, trailing=not money):
                        raise ValueError("Chart fact does not match its canonical QUARTER dates")
                    companions = (metric_id, *period_companions)
                    points.append(FinancialSeriesPoint(key, category, fact.fact_id, companions))
        figures.append(
            FinancialFigureSeries(
                fig_id,
                title,
                "grouped" if fig_id == "S.5" else "line",
                "amount" if money else "multiple",
                "US$m" if money else "x",
                series,
                tuple(points),
                reason,
            )
        )
    return tuple(figures)


def _states_dates(stated: str | None, dates: str, *, trailing: bool) -> bool:
    """Whether a chart fact states its quarter's `start to end` dates. A quarter's leverage and
    coverage (`trailing`) state the twelve months ending it instead (S13 C01)."""
    if stated is None:
        return False
    return stated.rsplit(": ", 1)[-1] == dates or (
        trailing and states_trailing_period(stated, dates.rpartition(" to ")[2])
    )


_FACILITY_FIELDS = (
    "facility_id",
    "facility_name",
    "period_id",
    "facility_type",
    "principal",
    "currency",
    "maturity_date",
    "annual_amortisation",
    "lease_classification",
)


def _facility_rows(
    rows: tuple[dict[str, Fact], ...],
    period_ids: set[str] | frozenset[str],
    unplotted: frozenset[str],
) -> dict[tuple[str, str], dict[str, Fact]]:
    """The T4.18 rows by (facility, period). Every row must be complete and dated at a T4.14
    period; a row dated at a YTD or LTM period is checked and then left out, as the period is."""
    indexed: dict[tuple[str, str], dict[str, Fact]] = {}
    for row in rows:
        if not frozenset(_FACILITY_FIELDS) <= row.keys():
            raise ValueError("Incomplete facility chart coordinates")
        fid, pid = _text(row["facility_id"]), _text(row["period_id"])
        if pid not in period_ids or any(f.period != pid for f in row.values()):
            raise ValueError("Foreign facility period")
        if pid in unplotted:
            continue
        if (fid, pid) in indexed:
            raise ValueError("Duplicate facility snapshot identity")
        indexed[fid, pid] = row
    return indexed


def _maturity_figure(
    module: ModuleView, periods: tuple[_Period, ...], unplotted: frozenset[str]
) -> FinancialFigureSeries:
    rows = _rows(module, "T4.18")
    title = "Maturity wall"
    reason = "No complete current facility snapshot is supplied."
    points: list[FinancialSeriesPoint] = []
    series: list[str] = []
    if periods:
        latest = max(p.end for p in periods)
        current = tuple(p for p in periods if p.end == latest)
        # An explicit reported quarter wins over its FY alias, never by value or label.
        selected = tuple(p for p in current if p.kind == "QUARTER") or current
        if len(selected) != 1:
            raise ValueError("Ambiguous current facility snapshot period")
        period = selected[0]
        title = f"Maturity wall — principal at {latest.isoformat()} (not a forecast)"
        indexed = _facility_rows(rows, {p.identity for p in periods} | unplotted, unplotted)
        population = {fid for fid, _ in indexed}
        actual = {fid for fid, pid in indexed if pid == period.identity}
        if population and actual == population:
            reason = ""
            for fid in sorted(population):
                row = indexed[fid, period.identity]
                # FY/Q4 are aliases only when the facility identity AND its terms agree.
                for alias in current:
                    other = indexed.get((fid, alias.identity))
                    # The selected quarter's snapshot is complete; an alias without this
                    # facility's row has nothing to compare, and is not plotted.
                    if other is None or other is row:
                        continue
                    for key in _FACILITY_FIELDS:
                        if key == "period_id":
                            continue
                        a, b = row[key], other[key]
                        if (a.amount, a.text, a.status, a.unit, a.currency, a.scale, a.basis) != (
                            b.amount,
                            b.text,
                            b.status,
                            b.unit,
                            b.currency,
                            b.scale,
                            b.basis,
                        ):
                            raise ValueError("Conflicting same-date facility snapshot aliases")
                if (
                    _text(row["currency"]) != "USD"
                    or _text(row["lease_classification"]) != "NOT_LEASE"
                ):
                    raise ValueError("Unsupported facility currency or lease scope")
                _numeric(row["principal"], True)
                if row["maturity_date"].status != "known":
                    reason = f"Contractual maturity unavailable: {row['maturity_date'].fact_id}"
                    break
                maturity = date.fromisoformat(_text(row["maturity_date"]))
                label = f"{_text(row['facility_name'])} ({fid})"
                companions = tuple(
                    row[k].fact_id for k in _FACILITY_FIELDS if k != "principal"
                ) + tuple(period.row[k].fact_id for k in _PERIOD_FIELDS)
                series.append(label)
                points.append(
                    FinancialSeriesPoint(
                        label, maturity.isoformat(), row["principal"].fact_id, companions
                    )
                )
    return FinancialFigureSeries(
        "S.4",
        title,
        "grouped",
        "amount",
        "US$m",
        tuple(series) if not reason else (),
        tuple(points) if not reason else (),
        reason or None,
    )


_SCOPE_FIELDS = ("currency", "unit", "accounting_basis", "entity_perimeter")
_SUPPORTED_SCOPE = ("USD", "MILLIONS", "IFRS", "consolidated group")
_SCOPE_REASON = (
    "Charts support USD millions on an IFRS consolidated group basis; this register states "
    "another currency, unit, accounting basis or perimeter; nothing was converted."
)


def _states_other_scope(module: ModuleView) -> bool:
    """Whether a T4.14 period states a known currency, unit, basis and perimeter that are not the
    supported scope. An incomplete or unresolved identity is left to `_periods`, which raises."""
    for row in _rows(module, "T4.14"):
        facts = [row.get(key) for key in _SCOPE_FIELDS]
        stated = tuple(f.text for f in facts if f is not None and f.status == "known")
        if len(stated) == len(_SCOPE_FIELDS) and None not in stated and stated != _SUPPORTED_SCOPE:
            return True
    return False


def _unsupported_scope_figures() -> tuple[FinancialFigureSeries, ...]:
    """S.1 to S.5 with no points, each carrying the unsupported-scope reason."""
    kinds: dict[str, Literal["line", "grouped"]] = {"S.4": "grouped", "S.5": "grouped"}
    titles = {fig_id: title for fig_id, title, _ in _SERIES} | {"S.4": "Maturity wall"}
    return tuple(
        FinancialFigureSeries(
            fig_id,
            titles[fig_id],
            kinds.get(fig_id, "line"),
            "multiple" if fig_id in {"S.1", "S.2"} else "amount",
            "x" if fig_id in {"S.1", "S.2"} else "US$m",
            (),
            (),
            _SCOPE_REASON,
        )
        for fig_id in ("S.1", "S.2", "S.3", "S.4", "S.5")
    )


def cp1_chart_series(module: ModuleView) -> tuple[FinancialFigureSeries, ...]:
    """Project settled CP1 facts; inactive/foreign modules have no numeric series.

    Incomplete reported-quarter coverage and missing current facility/maturity
    evidence produce explicit unsupported figures. Missing metric/basis coordinates
    and inconsistent accepted identities fail closed instead of becoming source gaps.
    A complete selected facility register is an upstream validation prerequisite;
    this projection can detect missing historical identities at the current date,
    but cannot establish completeness for an issuer outside the qualified case.
    """
    if module.module_id != "CP-1" or module.status not in {"accepted", "restricted"}:
        return ()
    if not module.artifact_sha256:
        raise ValueError("Settled CP1 chart facts require an artifact identity")
    if len({f.fact_id for f in module.facts}) != len(module.facts):
        raise ValueError("Duplicate chart fact identity")
    if _states_other_scope(module):
        return _unsupported_scope_figures()
    periods, unplotted = _periods(module)
    *strip, period_figure = _quarter_figures(module, periods)
    return (*strip, _maturity_figure(module, periods, unplotted), period_figure)
