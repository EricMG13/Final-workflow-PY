"""Scoped historical CP-MODEL readiness; calculation success alone is insufficient."""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

from deploy_vii.contracts import Contract, Hash, Identifier, Text
from deploy_vii.financial_contracts import (
    FinancialBook,
    FinancialPeriod,
    FinancialReview,
    Observation,
)
from deploy_vii.financial_periods import HistoricalReport, HistoricalValue, PeriodConstruction
from deploy_vii.financial_reconciliation import ReconciliationReport, reconcile_financials
from deploy_vii.financial_validation import records, validate_financial_review
from deploy_vii.model.dates import fiscal_year_number
from deploy_vii.model.history import BALANCE_METRICS
from deploy_vii.model.periods import LTM_DAYS
from deploy_vii.period_reconciliation import (
    PeriodCheck,
    PeriodReconciliationReport,
    _source_periods,
    reconcile_periods,
)
from deploy_vii.preparation import PreparedPack

# r14's Model interface flow coverage, with the two financing cash classifications
# needed by the reviewed kernel's adjusted CFO. Unknown is never an inferred zero.
REQUIRED_FLOWS = frozenset(
    {
        "revenue",
        "cogs",
        "opex_including_da",
        "depreciation_amortization",
        "ebitda",
        "adjusted_ebitda",
        "cash_interest_paid",
        "cash_lease_payments",
        "cash_taxes_paid",
        "cfo_ncfo",
        "working_capital_change",
        "capex_and_intangible_investment",
        "acquisitions_disposals",
        "net_debt_issue_repay",
        "net_equity_issue_repay",
        "dividends_paid",
        "other_investing_financing",
        "net_cash_change",
        "lease_payments_in_financing",
        "interest_paid_in_financing",
    }
)
_MANDATORY_CHECKS = frozenset(
    {
        "SEGMENT_REVENUE",
        "EBITDA_BRIDGE",
        "ADJUSTED_EBITDA_BRIDGE",
        "CFO_IDENTITY",
        "NCF_IDENTITY",
        "DEBT_TOTAL_EX_LEASES",
        "NCF_CASH_MOVEMENT",
    }
)


class ReadinessFinding(Contract):
    code: Identifier
    severity: Literal["BLOCK", "WARN"]
    construction_id: Identifier | None = None
    references: tuple[Text, ...] = ()
    explanation: Text


class ModelReadinessRow(Contract):
    downstream_module: Literal["CP-MODEL"] = "CP-MODEL"
    scope: Literal["selected_historical_quarters"] = "selected_historical_quarters"
    status: Literal["ready", "blocked"]
    selected_quarters: tuple[Identifier, ...]
    missing_metric_ids: tuple[Text, ...]
    conflict_refs: tuple[Identifier, ...]
    mandatory_check_ids: tuple[Identifier, ...]
    findings: tuple[ReadinessFinding, ...]
    explanation: Text


class ModelReadinessReport(Contract):
    schema_version: Literal["model-readiness/3"] = "model-readiness/3"
    run_id: Identifier
    issuer_id: Identifier
    as_of: date
    method_version: Literal["deploy-v-r14"] = "deploy-v-r14"
    pack_sha256: Hash
    review_sha256: Hash
    book_id: Identifier
    requested_quarters: tuple[Text, ...] | None
    readiness: ModelReadinessRow
    period_reconciliation: PeriodReconciliationReport | None
    source_reconciliation: ReconciliationReport
    limitations: tuple[Text, ...]


# --- the readiness findings (pure helpers of `_evaluate`) ------------------------------------
# A series cell with no source row in the column (`model._cells.ABSENT`). For an add-back, a
# sparse series CP-1 writes only for the periods it occurred in, that absence is nothing
# (`model.history._sum`), not an unknown input; every other required input stays unknown.
_NOT_SOURCED = "NOT_SOURCED"
_SPARSE_SCHEDULE = "addback:"
_YEAR_CHECKS = frozenset({"FY_QUARTERS", "REPORTED_DERIVED_PERIOD"})


def _finding(
    code: str,
    text: str,
    node: str | None = None,
    refs: tuple[str, ...] = (),
    *,
    warning: bool = False,
) -> ReadinessFinding:
    return ReadinessFinding(
        code=code,
        severity="WARN" if warning else "BLOCK",
        construction_id=node,
        references=refs,
        explanation=text,
    )


def _selection(
    available: Mapping[str, PeriodConstruction], requested: tuple[str, ...] | None
) -> tuple[list[PeriodConstruction], list[ReadinessFinding]]:
    """The selected quarters in date order, and a finding naming each duplicate or unknown id."""
    selected = tuple(available) if requested is None else requested
    counts = Counter(selected)
    wrong = tuple(dict.fromkeys(k for k in selected if counts[k] > 1 or k not in available))
    findings = []
    if wrong:
        text = "Selection contains duplicate or unknown quarter construction IDs: "
        findings.append(_finding("quarter_selection", text + ", ".join(wrong), refs=wrong))
    quarters = sorted(
        (available[key] for key in dict.fromkeys(selected) if key in available),
        key=lambda n: (n.end_date or date.min, n.construction_id),
    )
    return quarters, findings


def _slot(quarter: PeriodConstruction) -> int | None:
    """The quarter's fiscal slot, 4 x year + quarter, or None when either is unknown."""
    year = fiscal_year_number(quarter.fiscal_year)
    if year is None or quarter.fiscal_quarter is None:
        return None
    return 4 * year + quarter.fiscal_quarter


def _follows(previous: PeriodConstruction, quarter: PeriodConstruction) -> bool:
    return (
        previous.end_date is not None
        and quarter.start_date is not None
        and quarter.start_date - previous.end_date == timedelta(days=1)
    )


def _annual(first: PeriodConstruction, last: PeriodConstruction) -> bool:
    start, end = first.start_date, last.end_date
    return (
        start is not None
        and end is not None
        and LTM_DAYS[0] <= (end - start).days + 1 <= LTM_DAYS[1]
    )


def _quarter_findings(quarters: Sequence[PeriodConstruction]) -> list[ReadinessFinding]:
    """Count, span (with the construction's own limitation), continuity, fiscal sequence and
    four-quarter span of the selection."""
    findings = []
    if len(quarters) < 4:
        text = "At least four discrete complete quarters are required"
        findings.append(_finding("quarter_count", text))
    slots = [_slot(quarter) for quarter in quarters]
    for index, quarter in enumerate(quarters):
        cid = quarter.construction_id
        if None in (quarter.start_date, quarter.end_date, quarter.days) or quarter.limitation:
            text = "Quarter span is unavailable or not comparable"
            limitation = f": {quarter.limitation}" if quarter.limitation else ""
            findings.append(_finding("quarter_span", text + limitation, cid))
        if index and not _follows(quarters[index - 1], quarter):
            text = "Selected quarters must be contiguous and non-overlapping"
            findings.append(_finding("quarter_continuity", text, cid))
        slot, previous = slots[index], slots[index - 1] if index else None
        if slot is None or (index and (previous is None or slot != previous + 1)):
            text = "Selected fiscal quarter slots are not consecutive"
            findings.append(_finding("fiscal_sequence", text, cid))
        if index >= 3 and not _annual(quarters[index - 3], quarter):
            text = "Each four-quarter window must span 364-371 days"
            findings.append(_finding("annual_span", text, cid))
    return findings


@dataclass(frozen=True)
class _Scope:
    """What the selection reads of the book: each quarter's source periods (`leaves`, as the
    kernel's flow plan follows them) and their ids (`used`); every book period that is used,
    undated or overlaps the selected window (`periods`); and the window. `periods` and
    `window` are None where the window is unknown, and then every record is in scope."""

    leaves: Mapping[str, tuple[tuple[str | None, int], ...]]
    used: frozenset[str]
    known: frozenset[str]
    periods: frozenset[str] | None
    window: tuple[date, date] | None


def _side(period: FinancialPeriod, window: tuple[date, date]) -> int:
    """-1 for a period ending before the window, 1 for one starting after it, else 0 (it
    overlaps the window, or it is undated)."""
    first = period.start_date or period.end_date
    last = period.end_date or period.start_date
    if first is None or last is None:
        return 0
    return -1 if last < window[0] else 1 if first > window[1] else 0


def _scope(
    book: FinancialBook, historical: HistoricalReport, quarters: Sequence[PeriodConstruction]
) -> _Scope:
    leaves = {q.construction_id: _source_periods(historical, q) for q in quarters}
    used = frozenset(pid for terms in leaves.values() for pid, _ in terms if pid is not None)
    known = frozenset(p.period_id for p in book.periods)
    start = quarters[0].start_date if quarters else None
    end = quarters[-1].end_date if quarters else None
    if start is None or end is None:
        return _Scope(leaves, used, known, None, None)
    inside = {p.period_id for p in book.periods if _side(p, (start, end)) == 0}
    return _Scope(leaves, used, known, used | inside, (start, end))


def _in_scope(period_ids: set[str], scope: _Scope, book: FinancialBook) -> bool:
    """Whether rows in `period_ids` bear on the selection: no window is known, a row is in or
    across the window (rows on both sides of it), or a row's period is undated or unknown."""
    if scope.periods is None or scope.window is None or not period_ids:
        return True
    if period_ids & scope.periods or period_ids - scope.known:
        return True
    window = scope.window
    sides = {_side(p, window) for p in book.periods if p.period_id in period_ids}
    return {-1, 1} <= sides


def _period_ids(record: BaseModel) -> set[str]:
    """The period ids a book record names in its own fields (`period_id`, `annual_period_id`,
    `quarter_period_ids`, ...)."""
    found: set[str] = set()
    for name in type(record).model_fields:
        value = getattr(record, name)
        if name.endswith("period_id") and isinstance(value, str):
            found.add(value)
        elif name.endswith("period_ids") and isinstance(value, tuple):
            found.update(item for item in value if isinstance(item, str))
    return found


def _schedule(book: FinancialBook, scope: _Scope) -> tuple[tuple[str, ...], list[ReadinessFinding]]:
    """The schedule input keys each selected quarter requires: every facility and segment with
    a row in or across the selected window, and every add-back (absent, it is nothing). A
    series outside the window is a WARN that names it."""
    series: dict[str, set[str]] = {}
    for prefix, rows in (
        ("fac:", ((r.facility_id, r.period_id) for r in book.facilities)),
        ("bu:", ((r.segment_id, r.period_id) for r in book.segments)),
        (_SPARSE_SCHEDULE, ((r.addback_id, r.period_id) for r in book.addbacks)),
    ):
        for series_id, period_id in rows:
            series.setdefault(prefix + series_id, set()).add(period_id)
    required = tuple(
        key
        for key, ids in series.items()
        if key.startswith(_SPARSE_SCHEDULE) or _in_scope(ids, scope, book)
    )
    findings = []
    if not any(key.startswith("fac:") for key in required):
        text = "A complete carrying-value facility schedule is required"
        findings.append(_finding("facility_schedule", text))
    if outside := tuple(key for key in series if key not in required):
        text = "Schedule series with no row in or across the selected quarters are not required"
        findings.append(_finding("schedule_scope", text, refs=outside, warning=True))
    return required, findings


def _input_finding(row: HistoricalValue | None, cid: str, key: str) -> ReadinessFinding | None:
    """A required input that is unknown, or known without located evidence; an add-back with no
    source row in the quarter is nothing."""
    if row is None or row.value.amount is None:
        nothing = (
            row is not None
            and key.startswith(_SPARSE_SCHEDULE)
            and row.value.reason == _NOT_SOURCED
        )
        text = "Required historical input is unknown"
        return None if nothing else _finding("missing_input", text, cid, (key,))
    if not row.value.citations:
        text = "Required historical input has no located evidence"
        return _finding("source_locator", text, cid, (key,))
    return None


def _input_findings(
    book: FinancialBook,
    historical: HistoricalReport,
    quarters: Sequence[PeriodConstruction],
    scope: _Scope,
) -> tuple[list[ReadinessFinding], set[str], dict[int | None, set[str]]]:
    """Each selected quarter's required inputs: the findings, the missing metric ids and the
    flow metrics required in each fiscal year."""
    rows = {(v.construction_id, v.series_key): v for v in historical.values}
    by_period = {p.period_id: p for p in book.periods}
    schedule, findings = _schedule(book, scope)
    missing: set[str] = set()
    required_by_year: dict[int | None, set[str]] = {}
    for quarter in quarters:
        cid = quarter.construction_id
        leaves = scope.leaves[cid]
        nature = bool(leaves) and all(
            pid is not None and by_period[pid].expense_presentation == "by_nature"
            for pid, _ in leaves
        )
        flow_metrics = REQUIRED_FLOWS - ({"cogs"} if nature else set())
        year = fiscal_year_number(quarter.fiscal_year)
        required_by_year.setdefault(year, set()).update(flow_metrics)
        accounts = ("acct:" + metric for metric in sorted(flow_metrics | BALANCE_METRICS))
        for key in (*accounts, *schedule):
            found = _input_finding(rows.get((cid, key)), cid, key)
            if found is not None:
                missing.update(found.references if found.code == "missing_input" else ())
                findings.append(found)
        tax = rows.get((cid, "acct:effective_tax_rate"))
        components = [
            rows.get((cid, "acct:" + key)) for key in ("pretax_income", "income_tax_expense")
        ]
        if (tax is None or tax.value.amount is None) and any(
            v is None or v.value.amount is None for v in components
        ):
            missing.add("effective_tax_rate_or_pretax_and_tax")
            text = "Tax rate requires a source rate or both pretax income and tax expense"
            findings.append(_finding("tax_inputs", text, cid))
    return findings, missing, required_by_year


def _year_check(
    check: PeriodCheck,
    nodes: Mapping[str, PeriodConstruction],
    selected_years: set[int | None],
    required_by_year: Mapping[int | None, set[str]],
) -> bool:
    """An FY or reported-derived comparison of a selected fiscal year that bears on it."""
    if check.check_type not in _YEAR_CHECKS:
        return False
    year = fiscal_year_number(nodes[check.construction_id].fiscal_year)
    if year not in selected_years:
        return False
    return check.reported.amount is not None or (
        check.check_type == "FY_QUARTERS" and check.metric_id in required_by_year.get(year, set())
    )


def _check_findings(
    periods: PeriodReconciliationReport,
    quarters: Sequence[PeriodConstruction],
    required_by_year: Mapping[int | None, set[str]],
) -> tuple[list[ReadinessFinding], list[str]]:
    """Every selected quarter carries all mandatory comparisons (a WARN/null segment comparison
    for genuine non-disclosure included); each one not passing is a finding, and each absent
    type is named."""
    selected_ids = {q.construction_id for q in quarters}
    selected_years = {fiscal_year_number(q.fiscal_year) for q in quarters}
    nodes = {n.construction_id: n for n in periods.historical.constructions}
    findings: list[ReadinessFinding] = []
    mandatory: list[str] = []
    check_kinds: dict[str, set[str]] = {}
    for check in periods.checks:
        check_kinds.setdefault(check.construction_id, set()).add(check.check_type)
        selected_check = (
            check.construction_id in selected_ids and check.check_type in _MANDATORY_CHECKS
        )
        if selected_check or _year_check(check, nodes, selected_years, required_by_year):
            mandatory.append(check.check_id)
            if check.status != "PASS":
                findings.append(
                    _finding(
                        "reconciliation",
                        check.explanation,
                        check.construction_id,
                        (check.check_id,),
                        warning=check.status == "WARN",
                    )
                )
    for quarter in quarters:
        cid = quarter.construction_id
        if absent := tuple(sorted(_MANDATORY_CHECKS - check_kinds.get(cid, set()))):
            text = "Mandatory reconciliation types are absent: " + ", ".join(absent)
            findings.append(_finding("missing_checks", text, cid, absent))
    return findings, mandatory


def _conflicts(book: FinancialBook, scope: _Scope) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The conflicting observation ids of the book records in scope, then of those outside it,
    each in book order."""
    inside: list[str] = []
    outside: list[str] = []
    for name in type(book).model_fields:
        value = getattr(book, name)
        for record in value if isinstance(value, tuple) else (value,):
            if not isinstance(record, BaseModel):
                continue
            ids = [
                o.observation_id for o in records(record, Observation) if o.status == "conflicting"
            ]
            (inside if _in_scope(_period_ids(record), scope, book) else outside).extend(ids)
    return tuple(inside), tuple(outside)


def _scope_findings(
    book: FinancialBook, source: ReconciliationReport, scope: _Scope
) -> tuple[list[ReadinessFinding], list[str], tuple[str, ...]]:
    """Source checks of the used periods, the source conflicts in scope (a conflict outside it
    is a WARN that names it) and the forecast terms of the used periods' facilities: the
    findings, the mandatory source check ids and the blocking conflict ids."""
    findings: list[ReadinessFinding] = []
    mandatory: list[str] = []
    # A source error must not disappear through period subtraction. Derived FY
    # checks replace the direct-only quarterly comparison, which lacks computed Q4.
    for check in source.checks:
        if (
            check.period_id in scope.used
            and check.check_type != "FY_QUARTERS"
            and (
                check.check_type in {"SOURCE_STATEMENT_IDENTITY", "BALANCE_MOVEMENT"}
                or check.difference is not None
            )
        ):
            mandatory.append(check.check_id)
            if check.status != "PASS":
                findings.append(
                    _finding(
                        "source_reconciliation",
                        check.explanation,
                        refs=(check.check_id,),
                        warning=check.status == "WARN",
                    )
                )
    conflicts, outside = _conflicts(book, scope)
    if conflicts:
        text = "Unresolved source conflicts require explicit resolution"
        findings.append(_finding("source_conflicts", text, refs=conflicts))
    if outside:
        text = "Unresolved source conflicts outside the selected quarters do not block them"
        findings.append(_finding("source_conflicts_outside", text, refs=outside, warning=True))
    for facility in book.facilities:
        if facility.period_id in scope.used and (
            facility.rate_type == "NOT_STATED"
            or facility.annual_amortisation.amount is None
            or facility.maturity_date is None
        ):
            findings.append(
                _finding(
                    "facility_terms",
                    "Historical carrying value does not establish forecast rate, "
                    "amortisation or maturity terms",
                    refs=(facility.facility_id, facility.period_id),
                    warning=True,
                )
            )
    return findings, mandatory, conflicts


def _evaluate(
    book: FinancialBook,
    periods: PeriodReconciliationReport,
    source: ReconciliationReport,
    requested: tuple[str, ...] | None,
) -> ModelReadinessRow:
    """The CP-MODEL row over the selected historical quarters: every finding is scoped to
    them (their source periods, or book records in or across their window)."""
    historical = periods.historical
    available = {n.construction_id: n for n in historical.constructions if n.kind == "QUARTER"}
    quarters, findings = _selection(available, requested)
    findings += _quarter_findings(quarters)
    scope = _scope(book, historical, quarters)
    inputs, missing, required_by_year = _input_findings(book, historical, quarters, scope)
    checks, mandatory = _check_findings(periods, quarters, required_by_year)
    scoped, source_mandatory, conflicts = _scope_findings(book, source, scope)
    findings += [*inputs, *checks, *scoped]
    ready = not any(f.severity == "BLOCK" for f in findings)
    return ModelReadinessRow(
        status="ready" if ready else "blocked",
        selected_quarters=tuple(q.construction_id for q in quarters),
        missing_metric_ids=tuple(sorted(missing)),
        conflict_refs=conflicts,
        mandatory_check_ids=tuple(dict.fromkeys((*mandatory, *source_mandatory))),
        findings=tuple(findings),
        explanation="Selected historical quarters satisfy deterministic Model input requirements"
        if ready
        else "Selected historical quarters do not satisfy Model input requirements",
    )


def assess_model_readiness(
    pack: PreparedPack,
    review: FinancialReview,
    book_id: str,
    *,
    quarter_ids: tuple[str, ...] | None = None,
) -> ModelReadinessReport:
    issues = validate_financial_review(pack, review)
    if issues:
        raise ValueError("; ".join(issues))
    review = FinancialReview.model_validate_json(review.model_dump_json())
    book = next((b for b in review.books if b.book_id == book_id), None)
    if book is None:
        raise ValueError(f"Unknown financial book: {book_id}")
    source = reconcile_financials(pack, review, book_id)
    periods: PeriodReconciliationReport | None = None
    try:
        periods = reconcile_periods(pack, review, book_id)
    except ValueError as error:
        row = ModelReadinessRow(
            status="blocked",
            selected_quarters=(),
            missing_metric_ids=(),
            conflict_refs=tuple(
                o.observation_id for o in records(book, Observation) if o.status == "conflicting"
            ),
            mandatory_check_ids=(),
            findings=(
                ReadinessFinding(code="input_conversion", severity="BLOCK", explanation=str(error)),
            ),
            explanation="Source review cannot enter historical Model calculation",
        )
    else:
        row = _evaluate(book, periods, source, quarter_ids)
    return ModelReadinessReport(
        run_id=review.run_id,
        issuer_id=review.issuer_id,
        as_of=review.as_of,
        pack_sha256=review.pack_sha256,
        review_sha256=review.content_hash(),
        book_id=book_id,
        requested_quarters=quarter_ids,
        readiness=row,
        period_reconciliation=periods,
        source_reconciliation=source,
        limitations=(
            "Readiness applies only to the explicitly retained historical quarter scope",
            "A ready row does not qualify pro forma, projections, "
            "analytical interpretation or report delivery",
            "No downstream consumer other than CP-MODEL is assessed here",
            "Source-backed exceptions and full CP-1 acceptance remain separate",
        ),
    )


def validate_model_readiness(
    pack: PreparedPack, review: FinancialReview, report: ModelReadinessReport
) -> tuple[str, ...]:
    try:
        report = ModelReadinessReport.model_validate_json(report.model_dump_json())
        expected = assess_model_readiness(
            pack, review, report.book_id, quarter_ids=report.requested_quarters
        )
    except ValueError as error:
        return (f"Invalid Model readiness inputs: {error}",)
    return (
        ()
        if report.content_hash() == expected.content_hash()
        else ("Model readiness differs from deterministic recomputation",)
    )
