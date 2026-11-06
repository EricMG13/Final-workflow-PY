"""S05 review: the CP-MODEL readiness row is scoped to the selected historical quarters
(`ModelReadinessReport.limitations`: "Readiness applies only to the explicitly retained
historical quarter scope"), and every refusal names what failed.

The book is a real `FinancialBook` (FY2019 plus four FY2023 quarters). The period
reconciliation and source reports are attribute stand-ins: `_evaluate` reads only the
attributes set here, and every quarter carries every mandatory check, passing. Expected
values are literal ids and texts."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from deploy_vii.contracts import Citation
from deploy_vii.financial_contracts import (
    AddbackObservation,
    Alternative,
    Disclosure,
    FacilityObservation,
    FinancialBook,
    FinancialPeriod,
    KpiObservation,
    Observation,
)
from deploy_vii.model.history import BALANCE_METRICS
from deploy_vii.model_readiness import _MANDATORY_CHECKS, REQUIRED_FLOWS, _evaluate

CITE = Citation(source_id="s1", source_sha256="0" * 64, locator="p1", quote="q")
OTHER = Citation(source_id="s1", source_sha256="0" * 64, locator="p2", quote="r")
QUARTERS = ("q1", "q2", "q3", "q4")


def _known(amount: str = "1") -> Observation:
    return Observation(
        status="known", amount=Decimal(amount), citations=(CITE,), observation_id="o"
    )


def _missing() -> Observation:
    return Observation(
        observation_id="m", status="missing", amount=None, citations=(), reason="Not stated"
    )


def _conflict(observation_id: str) -> Observation:
    return Observation(
        observation_id=observation_id,
        status="conflicting",
        amount=None,
        citations=(),
        reason="Two figures",
        alternatives=(
            Alternative(amount=Decimal(1), citations=(CITE,), explanation="page 1"),
            Alternative(amount=Decimal(2), citations=(OTHER,), explanation="page 2"),
        ),
    )


def _period(pid: str, kind: Any, start: date, end: date, quarter: int | None) -> FinancialPeriod:
    return FinancialPeriod(
        period_id=pid,
        fiscal_year=f"FY{end.year}",
        fiscal_quarter=quarter,
        period_type=kind,
        start_date=start,
        end_date=end,
        day_count=(end - start).days + 1,
        audit_status="unaudited",
        currency="USD",
        unit="MILLIONS",
        accounting_basis="IFRS",
        entity_perimeter="Group",
        citations=(CITE,),
        expense_presentation="by_nature",
        presentation_citations=(CITE,),
    )


def _quarter_dates() -> list[tuple[date, date]]:
    out, start = [], date(2023, 1, 1)
    for _ in range(4):
        month = start.month + 3
        following = date(start.year + (month > 12), (month - 1) % 12 + 1, 1)
        out.append((start, following - timedelta(days=1)))
        start = following
    return out


DATES = _quarter_dates()
PERIODS = (
    _period("P0", "FY", date(2019, 1, 1), date(2019, 12, 31), None),
    *(_period(f"P{i}", "QUARTER", s, e, i) for i, (s, e) in enumerate(DATES, 1)),
)


def _facility(facility_id: str, period_id: str) -> FacilityObservation:
    return FacilityObservation(
        facility_id=facility_id,
        facility_name=facility_id,
        period_id=period_id,
        facility_type="TERM LOAN",
        currency="USD",
        carrying_value=_known("10"),
        principal=_known("10"),
        drawn_amount=_known("10"),
        commitment=_known("10"),
        secured_status="SECURED",
        seniority="SENIOR",
        lease_classification="NOT_LEASE",
        margin_or_coupon="5%",
        maturity_date=date(2030, 1, 1),
        maturity_limitation=None,
        rate_type="FIXED",
        reference_rate="NONE",
        spread_bps=_missing(),
        floor_bps=_missing(),
        fixed_rate=_known("0.05"),
        annual_amortisation=_known("0"),
        terms_citations=(CITE,),
    )


def _kpi(kpi_id: str, period_id: str, value: Observation) -> KpiObservation:
    return KpiObservation(
        kpi_id=kpi_id,
        kpi_label=kpi_id,
        business_unit="Group",
        kpi_category="Operating",
        definition="Subscribers",
        display_priority=1,
        period_id=period_id,
        value=value,
        unit="count",
        value_type="PERIOD_END",
        definition_citations=(CITE,),
    )


def _addback(addback_id: str, period_id: str) -> AddbackObservation:
    return AddbackObservation(
        addback_id=addback_id,
        addback_label="Restructuring",
        classification="RESTRUCTURING",
        realization_status="REALIZED",
        display_priority=1,
        period_id=period_id,
        value=_known("3"),
        source_definition="Restructuring costs",
        classification_citations=(CITE,),
    )


def _book(**records: Any) -> FinancialBook:
    disclosure = Disclosure(status="not_applicable", explanation="None", citations=(CITE,))
    fields: dict[str, Any] = {
        "accounts": (),
        "addbacks": (),
        "segments": (),
        "kpis": (),
        "facilities": (_facility("F1", "P4"),),
        "pro_forma": (),
        **records,
    }
    return FinancialBook(
        book_id="b",
        entity_perimeter="Group",
        accounting_basis="IFRS",
        currency="USD",
        unit="MILLIONS",
        periods=PERIODS,
        segment_allocation=(),
        addback_disclosure=disclosure,
        segment_disclosure=disclosure,
        **fields,
    )


def _value(cid: str, key: str, amount: str | None, reason: str | None = None) -> Any:
    citations = (CITE,) if amount is not None else ()
    value = SimpleNamespace(
        amount=None if amount is None else Decimal(amount), reason=reason, citations=citations
    )
    return SimpleNamespace(construction_id=cid, series_key=key, value=value)


def _reports(
    extra: tuple[Any, ...] = (), *, drop: tuple[tuple[str, str], ...] = ()
) -> tuple[Any, Any]:
    quarters = tuple(
        SimpleNamespace(
            construction_id=cid,
            kind="QUARTER",
            start_date=start,
            end_date=end,
            days=(end - start).days + 1,
            limitation=None,
            fiscal_year="FY2023",
            fiscal_quarter=index,
            terms=(),
            own_period_id=f"P{index}",
        )
        for index, (cid, (start, end)) in enumerate(zip(QUARTERS, DATES, strict=True), 1)
    )
    keys = ["acct:" + m for m in REQUIRED_FLOWS | BALANCE_METRICS | {"effective_tax_rate"}]
    values = [_value(cid, key, "1") for cid in QUARTERS for key in (*keys, "fac:F1")]
    checks = tuple(
        SimpleNamespace(
            check_id=f"{cid}-{kind}",
            construction_id=cid,
            check_type=kind,
            status="PASS",
            metric_id="x",
            reported=SimpleNamespace(amount=None),
            explanation="ok",
        )
        for cid in QUARTERS
        for kind in sorted(_MANDATORY_CHECKS)
        if (cid, kind) not in drop
    )
    historical = SimpleNamespace(constructions=quarters, values=(*values, *extra), periods=PERIODS)
    return SimpleNamespace(historical=historical, checks=checks), SimpleNamespace(checks=())


def _row(book: FinancialBook, extra: tuple[Any, ...] = (), **kwargs: Any) -> Any:
    periods, source = _reports(extra, drop=kwargs.pop("drop", ()))
    return _evaluate(book, periods, source, kwargs.pop("requested", None))


def _codes(row: Any) -> list[tuple[str, str, tuple[str, ...]]]:
    return [(f.code, f.severity, f.references) for f in row.findings]


def test_baseline_is_ready() -> None:
    row = _row(_book())
    assert (row.status, _codes(row)) == ("ready", [])


def test_a_conflict_outside_the_window_warns_and_does_not_block() -> None:
    book = _book(kpis=(_kpi("subscribers", "P0", _conflict("kpi-subscribers-FY2019")),))
    row = _row(book)
    assert row.status == "ready"
    assert row.conflict_refs == ()
    assert _codes(row) == [
        ("source_conflicts_outside", "WARN", ("kpi-subscribers-FY2019",)),
    ]


def test_a_conflict_in_a_selected_quarter_still_blocks() -> None:
    book = _book(kpis=(_kpi("subscribers", "P2", _conflict("kpi-subscribers-Q2")),))
    row = _row(book)
    assert row.status == "blocked"
    assert row.conflict_refs == ("kpi-subscribers-Q2",)
    assert _codes(row) == [("source_conflicts", "BLOCK", ("kpi-subscribers-Q2",))]


def test_out_of_window_facility_and_absent_addback_do_not_block() -> None:
    book = _book(
        facilities=(_facility("F1", "P4"), _facility("F0", "P0")),
        addbacks=(_addback("restructuring_2019", "P0"),),
    )
    absent = tuple(
        _value(cid, key, None, "NOT_SOURCED")
        for cid in QUARTERS
        for key in ("fac:F0", "addback:restructuring_2019")
    )
    row = _row(book, absent)
    assert row.status == "ready"
    assert row.missing_metric_ids == ()
    assert _codes(row) == [("schedule_scope", "WARN", ("fac:F0",))]


def test_a_facility_on_both_sides_of_the_window_is_still_required() -> None:
    later = _period("P9", "FY", date(2025, 1, 1), date(2025, 12, 31), None)
    book = _book(facilities=(_facility("F1", "P4"), _facility("F2", "P0"), _facility("F2", "P9")))
    book = book.model_copy(update={"periods": (*PERIODS, later)})
    absent = tuple(_value(cid, "fac:F2", None, "NOT_SOURCED") for cid in QUARTERS)
    row = _row(book, absent)
    assert row.status == "blocked"
    assert row.missing_metric_ids == ("fac:F2",)


def test_an_addback_component_missing_in_a_quarter_still_blocks() -> None:
    book = _book(addbacks=(_addback("restructuring", "P2"),))
    cells = (
        _value("q1", "addback:restructuring", None, "NOT_SOURCED"),
        _value("q2", "addback:restructuring", "3"),
        _value("q3", "addback:restructuring", None, "COMPONENT_MISSING"),
        _value("q4", "addback:restructuring", None, "NOT_SOURCED"),
    )
    row = _row(book, cells)
    assert row.status == "blocked"
    assert _codes(row) == [("missing_input", "BLOCK", ("addback:restructuring",))]
    assert [f.construction_id for f in row.findings] == ["q3"]


def test_a_bad_selection_names_the_duplicate_and_unknown_ids() -> None:
    row = _row(_book(), requested=("q1", "q2", "q3", "q4", "q4", "FY2023"))
    assert _codes(row) == [("quarter_selection", "BLOCK", ("q4", "FY2023"))]
    assert row.findings[0].explanation == (
        "Selection contains duplicate or unknown quarter construction IDs: q4, FY2023"
    )


def test_absent_check_types_are_named() -> None:
    row = _row(_book(), drop=(("q2", "CFO_IDENTITY"), ("q2", "NCF_IDENTITY")))
    assert [(f.code, f.construction_id, f.references, f.explanation) for f in row.findings] == [
        (
            "missing_checks",
            "q2",
            ("CFO_IDENTITY", "NCF_IDENTITY"),
            "Mandatory reconciliation types are absent: CFO_IDENTITY, NCF_IDENTITY",
        )
    ]


def test_a_quarter_span_keeps_the_construction_limitation() -> None:
    periods, source = _reports()
    quarter = periods.historical.constructions[1]
    quarter.limitation = "Q2 spans 14 weeks"
    row = _evaluate(_book(), periods, source, None)
    assert [(f.code, f.construction_id, f.explanation) for f in row.findings] == [
        ("quarter_span", "q2", "Quarter span is unavailable or not comparable: Q2 spans 14 weeks")
    ]
