"""Source-native chart coordinates from a selected settled CP1 register.

This projection selects facts, never calculates financial values or display text.
Its bounded support is four reported quarters of one fiscal year and a complete current
facility snapshot, in millions of the one currency the T4.14 register states, IFRS
consolidated group. A register that states several currencies (or a facility stated in
another currency) gives its money figures an explicit unsupported reason; nothing is
converted. Authentication belongs to the unchanged envelope/publication boundary; a
ModuleView alone is not that proof.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from operator import attrgetter
from typing import Literal

from deploy_vii.contracts import Fact, ModuleView
from deploy_vii.report_view import scale_label


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
_SERIES = (
    ("S.1", "Leverage", ("total_leverage_reported", "net_leverage_reported")),
    ("S.2", "Interest cover", ("interest_coverage_reported",)),
    ("S.3", "Liquidity", ("cash_closing", "undrawn_rcf", "liquidity")),
    # S.5 reads T4.10 `revenue` and `adjusted_ebitda` (T4.5 is the cash-flow statement).
    ("S.5", "Net revenues and Adjusted EBITDA", ("revenue", "adjusted_ebitda")),
)
_MONEY_FIGURES = frozenset({"S.3", "S.5"})
_CURRENCY_CODE = re.compile(r"[A-Z]{3}")
_USD_UNIT = "US$m"
_MIXED_CURRENCIES = (
    "The CP-1 period register states more than one currency ({}); "
    "no amount is converted and no money figure is charted."
)
_NOT_FOUR = "Charts require exactly four reported QUARTER periods; no periods were fabricated."
_NOT_ONE_YEAR = (
    "Charts require Q1 to Q4 of one fiscal year; the four reported QUARTER periods are {}; "
    "no periods were fabricated."
)
_NO_SNAPSHOT = "No complete current facility snapshot is supplied."
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
# The terms that make a same-date FY/Q4 facility row an alias of the other, never its label.
_TERMS = attrgetter("amount", "text", "status", "unit", "currency", "scale", "basis")


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


def _periods(module: ModuleView) -> tuple[_Period, ...]:
    periods = []
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
        if not _CURRENCY_CODE.fullmatch(scope[0]) or scope[1:] != (
            "MILLIONS",
            "IFRS",
            "consolidated group",
        ):
            raise ValueError("Unsupported chart currency, unit or perimeter")
        if any(f.basis != "IFRS · consolidated group" for f in row.values()):
            raise ValueError("Inconsistent chart period perimeter")
        kind = _text(row["period_type"])
        if kind not in {"QUARTER", "FY", "PERIOD_END"}:
            raise ValueError("Unsupported historical chart period type")
        periods.append(_Period(identity, kind, date.fromisoformat(_text(row["end_date"])), row))
    return tuple(sorted(periods, key=lambda p: (p.end, p.identity)))


@dataclass(frozen=True)
class _Money:
    """The register's one currency, or why its money figures are unsupported.

    `currency` is None when no period states one (an empty register) or several do; `reason`
    is set only for several, and every money figure then carries it instead of points.
    """

    currency: str | None
    reason: str | None

    @property
    def unit(self) -> str:
        # USD keeps the consumer's pinned spelling; a register with no one currency keeps the
        # parent's label, as `liquidity_series` does; any other currency is `scale_label`'s.
        if self.currency in (None, "USD"):
            return _USD_UNIT
        return scale_label("MILLIONS", self.currency) or _USD_UNIT


def _money(periods: tuple[_Period, ...]) -> _Money:
    found = sorted({_text(p.row["currency"]) for p in periods})
    if len(found) > 1:
        return _Money(None, _MIXED_CURRENCIES.format(", ".join(found)))
    return _Money(found[0] if found else None, None)


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


def _numeric(fact: Fact, currency: str | None) -> None:
    """Check a selected value's dimensions: millions of `currency`, or a multiple for None."""
    dimensions = (fact.unit, fact.currency, fact.scale, fact.basis)
    expected = (
        ("MILLIONS", currency, Decimal(1000000), "IFRS · consolidated group")
        if currency is not None
        else ("MULTIPLE", None, Decimal(1), "IFRS · consolidated group")
    )
    if dimensions != expected or fact.text is not None:
        raise ValueError(f"Incompatible chart dimensions: {fact.fact_id}")
    if fact.status == "known":
        if fact.amount is None or not fact.amount.is_finite():
            raise ValueError(f"Nonfinite or absent chart value: {fact.fact_id}")
    elif fact.amount is not None or not fact.limitation:
        raise ValueError(f"Invalid chart gap: {fact.fact_id}")


def _quarter_reason(quarters: tuple[_Period, ...]) -> str | None:
    """Why the quarters cannot be charted, or None for Q1 to Q4 of one fiscal year.

    Four quarters of another shape (a trailing four quarters across two fiscal years) are an
    unsupported reason like any other count; reversed, overlapping or, within one fiscal year,
    noncontiguous dates are inconsistent identities and raise.
    """
    if len(quarters) != 4:
        return _NOT_FOUR
    starts = tuple(date.fromisoformat(_text(p.row["start_date"])) for p in quarters)
    previous = (None, *(p.end for p in quarters[:-1]))
    if any(
        start > period.end or (end is not None and start <= end)
        for start, period, end in zip(starts, quarters, previous, strict=True)
    ):
        raise ValueError("Ambiguous or overlapping QUARTER identities")
    names = tuple(
        (_text(p.row["fiscal_year"]), _text(p.row["fiscal_quarter"]).removeprefix("Q"))
        for p in quarters
    )
    if names != tuple((names[0][0], number) for number in "1234"):
        return _NOT_ONE_YEAR.format(", ".join(map(_quarter_name, quarters)))
    if any(
        end is not None and start != end + timedelta(days=1)
        for start, end in zip(starts, previous, strict=True)
    ):
        raise ValueError("Ambiguous or noncontiguous QUARTER identities")
    return None


def _metric_rows(module: ModuleView) -> dict[str, dict[str, Fact]]:
    metrics: dict[str, dict[str, Fact]] = {}
    for row in _rows(module, "T4.10"):
        if "field_1" not in row:
            raise ValueError("Missing KPI metric identity")
        key = _text(row["field_1"])
        if key in metrics:
            raise ValueError("Duplicate KPI metric identity")
        metrics[key] = row
    return metrics


_Coordinate = tuple[str, str, str, str, tuple[str, ...]]


def _quarter_name(period: _Period) -> str:
    """`Q<n> <fiscal year>`, the category of a quarter's point."""
    quarter = _text(period.row["fiscal_quarter"]).removeprefix("Q")
    return f"Q{quarter} {_text(period.row['fiscal_year'])}"


def _quarter_coordinates(quarters: tuple[_Period, ...]) -> tuple[_Coordinate, ...]:
    """(period id, canonical basis field, dates, category, period companions) per quarter."""
    return tuple(
        (
            period.identity,
            _basis(period.identity),
            f"{_text(period.row['start_date'])} to {period.end.isoformat()}",
            _quarter_name(period),
            tuple(period.row[k].fact_id for k in _PERIOD_FIELDS),
        )
        for period in quarters
    )


def _quarter_points(
    metrics: dict[str, dict[str, Fact]],
    series: tuple[str, ...],
    coordinates: tuple[_Coordinate, ...],
    currency: str | None,
) -> tuple[FinancialSeriesPoint, ...]:
    points = []
    for key in series:
        metric = metrics[key]
        metric_id = metric["field_1"].fact_id
        for identity, field, dates, category, period_companions in coordinates:
            if field not in metric:
                raise ValueError(f"Missing canonical QUARTER basis: {key}/{identity}")
            fact = metric[field]
            _numeric(fact, currency)
            if fact.period is None or fact.period.rsplit(": ", 1)[-1] != dates:
                raise ValueError("Chart fact does not match its canonical QUARTER dates")
            companions = (metric_id, *period_companions)
            points.append(FinancialSeriesPoint(key, category, fact.fact_id, companions))
    return tuple(points)


def _quarter_figures(
    module: ModuleView, periods: tuple[_Period, ...], money: _Money
) -> tuple[FinancialFigureSeries, ...]:
    quarters = tuple(p for p in periods if p.kind == "QUARTER")
    quarter_reason = _quarter_reason(quarters)
    metrics = _metric_rows(module)
    coordinates = _quarter_coordinates(quarters) if quarter_reason is None else ()
    figures = []
    for fig_id, title, series in _SERIES:
        is_money = fig_id in _MONEY_FIGURES
        for key in series:
            if key not in metrics:
                raise ValueError(f"Missing chart metric implementation: {key}")
        reason = quarter_reason or (money.reason if is_money else None)
        points = (
            _quarter_points(metrics, series, coordinates, money.currency if is_money else None)
            if reason is None
            else ()
        )
        figures.append(
            FinancialFigureSeries(
                fig_id,
                title,
                "grouped" if fig_id == "S.5" else "line",
                "amount" if is_money else "multiple",
                money.unit if is_money else "x",
                series,
                points,
                reason,
            )
        )
    return tuple(figures)


def _facility_index(
    rows: tuple[dict[str, Fact], ...], periods: tuple[_Period, ...]
) -> dict[tuple[str, str], dict[str, Fact]]:
    """The T4.18 rows by (facility id, period id); every row names a register period."""
    indexed: dict[tuple[str, str], dict[str, Fact]] = {}
    period_ids = {p.identity for p in periods}
    for row in rows:
        if not frozenset(_FACILITY_FIELDS) <= row.keys():
            raise ValueError("Incomplete facility chart coordinates")
        fid, pid = _text(row["facility_id"]), _text(row["period_id"])
        if pid not in period_ids or any(f.period != pid for f in row.values()):
            raise ValueError("Foreign facility period")
        if (fid, pid) in indexed:
            raise ValueError("Duplicate facility snapshot identity")
        indexed[fid, pid] = row
    return indexed


def _check_aliases(
    row: dict[str, Fact],
    fid: str,
    current: tuple[_Period, ...],
    indexed: dict[tuple[str, str], dict[str, Fact]],
) -> None:
    """FY/Q4 are aliases only when the facility identity AND its terms agree."""
    for alias in current:
        other = indexed.get((fid, alias.identity))
        if other is None:
            raise ValueError("Incomplete same-date facility snapshot alias")
        if other is row:
            continue
        if any(
            _TERMS(row[key]) != _TERMS(other[key]) for key in _FACILITY_FIELDS if key != "period_id"
        ):
            raise ValueError("Conflicting same-date facility snapshot aliases")


def _facility_reason(row: dict[str, Fact], fid: str, money: _Money) -> str | None:
    """Why this current facility row cannot be charted, or None once its principal checks."""
    if _text(row["lease_classification"]) != "NOT_LEASE":
        raise ValueError("Unsupported facility lease scope")
    stated = _text(row["currency"])
    if money.reason is not None:
        return money.reason
    if stated != money.currency:
        return (
            f"Facility {fid} is stated in {stated}, not the register currency "
            f"{money.currency}; no amount is converted."
        )
    _numeric(row["principal"], money.currency)
    if row["maturity_date"].status != "known":
        return f"Contractual maturity unavailable: {row['maturity_date'].fact_id}"
    return None


def _maturity(
    title: str, money: _Money, points: tuple[FinancialSeriesPoint, ...], reason: str | None
) -> FinancialFigureSeries:
    series = tuple(p.series for p in points)
    return FinancialFigureSeries(
        "S.4", title, "grouped", "amount", money.unit, series, points, reason
    )


def _maturity_figure(
    module: ModuleView, periods: tuple[_Period, ...], money: _Money
) -> FinancialFigureSeries:
    rows = _rows(module, "T4.18")
    if not periods:
        return _maturity("Maturity wall", money, (), _NO_SNAPSHOT)
    latest = max(p.end for p in periods)
    current = tuple(p for p in periods if p.end == latest)
    # An explicit reported quarter wins over its FY alias, never by value or label.
    selected = tuple(p for p in current if p.kind == "QUARTER") or current
    if len(selected) != 1:
        raise ValueError("Ambiguous current facility snapshot period")
    period = selected[0]
    title = f"Maturity wall — principal at {latest.isoformat()} (not a forecast)"
    indexed = _facility_index(rows, periods)
    population = {fid for fid, _ in indexed}
    if not population or {fid for fid, pid in indexed if pid == period.identity} != population:
        return _maturity(title, money, (), _NO_SNAPSHOT)
    points = []
    for fid in sorted(population):
        row = indexed[fid, period.identity]
        _check_aliases(row, fid, current, indexed)
        reason = _facility_reason(row, fid, money)
        if reason is not None:
            return _maturity(title, money, (), reason)
        label = f"{_text(row['facility_name'])} ({fid})"
        companions = tuple(row[k].fact_id for k in _FACILITY_FIELDS if k != "principal") + tuple(
            period.row[k].fact_id for k in _PERIOD_FIELDS
        )
        maturity = date.fromisoformat(_text(row["maturity_date"])).isoformat()
        points.append(FinancialSeriesPoint(label, maturity, row["principal"].fact_id, companions))
    return _maturity(title, money, tuple(points), None)


def cp1_chart_series(module: ModuleView) -> tuple[FinancialFigureSeries, ...]:
    """Project settled CP1 facts; inactive/foreign modules have no numeric series.

    Incomplete reported-quarter coverage, quarters that are not Q1 to Q4 of one fiscal year,
    a register stating several currencies and missing current facility/maturity evidence
    produce explicit unsupported figures. Missing metric/basis coordinates and inconsistent
    accepted identities fail closed instead of becoming source gaps.
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
    periods = _periods(module)
    money = _money(periods)
    *strip, period_figure = _quarter_figures(module, periods, money)
    return (*strip, _maturity_figure(module, periods, money), period_figure)
