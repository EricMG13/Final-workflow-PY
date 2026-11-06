"""S05 review: Model interface cells keep what the source states.

- a zero outflow is zero, never "-0" (`model._cells.no_negative_zero`, as the kernel reads it);
- an observation stated `not_applicable` is no data gap;
- a facility's maturity limitation qualifies a stated maturity date;
- each period's schedule row carries that period's own name, classification and unit;
- the readiness row names every readiness finding (code, quarter, references, explanation).

The book is the real `FinancialBook` of `test_review_s05_model_readiness_scope`."""

from decimal import Decimal
from typing import Any

import test_review_s05_model_readiness_scope as fx

from deploy_vii.financial_contracts import KpiObservation, Observation, SegmentObservation
from deploy_vii.model_interface import _facilities, _finding_text, _observed, _schedules, _Tables
from deploy_vii.model_readiness import ReadinessFinding


def _facts(tables: _Tables, table: str, field: str) -> dict[str, Any]:
    return {f.row_id: f for f in tables.facts if f.table_id == table and f.field == field}


def test_a_zero_outflow_is_zero() -> None:
    cell = _observed(fx._known("0"), fx._book(), outflow=True)
    assert str(cell.value) == "0"
    assert cell.value_class == "source"
    assert cell.source_amount == Decimal(0)
    negative = _observed(fx._known("5"), fx._book(), outflow=True)
    assert (str(negative.value), negative.value_class) == ("-5", "normalized")


def test_a_not_applicable_observation_is_no_gap() -> None:
    stated = Observation(
        observation_id="commitment",
        status="not_applicable",
        amount=None,
        citations=(fx.CITE,),
        reason="A term loan has no commitment",
    )
    facility = fx._facility("F1", "P4").model_copy(update={"commitment": stated})
    tables = _Tables(fx._book(facilities=(facility,)))
    _facilities(tables)
    assert tables.gaps == []
    (commitment,) = _facts(tables, "T4.18", "commitment").values()
    assert (commitment.status, commitment.limitation) == (
        "not_applicable",
        "A term loan has no commitment",
    )


def test_a_maturity_limitation_qualifies_a_stated_date() -> None:
    facility = fx._facility("F1", "P4").model_copy(
        update={"maturity_limitation": "Springs 91 days before the notes"}
    )
    tables = _Tables(fx._book(facilities=(facility,)))
    _facilities(tables)
    (maturity,) = _facts(tables, "T4.18", "maturity_date").values()
    assert (maturity.text, maturity.limitation) == (
        "2030-01-01",
        "Springs 91 days before the notes",
    )


def _segment(name: str, period_id: str, priority: int) -> SegmentObservation:
    return SegmentObservation(
        segment_id="S1",
        segment_name=name,
        segment_type="OPERATING_SEGMENT",
        display_priority=priority,
        period_id=period_id,
        revenue=fx._known("7"),
        classification_citations=(fx.CITE,),
    )


def _kpi(unit: str, period_id: str) -> KpiObservation:
    return fx._kpi("arpu", period_id, fx._known("3")).model_copy(update={"unit": unit})


def test_each_period_keeps_its_own_schedule_attributes() -> None:
    book = fx._book(
        segments=(_segment("Consumer", "P1", 1), _segment("Retail", "P2", 2)),
        kpis=(_kpi("USD", "P1"), _kpi("EUR", "P2")),
    )
    tables = _Tables(book)
    _schedules(tables)
    names = {
        f.period: f.text
        for f in tables.facts
        if f.table_id == "T4.16" and f.field == "segment_name"
    }
    assert (names["P1"], names["P2"], names["P3"]) == ("Consumer", "Retail", "Retail")
    priority = {
        f.period: f.text
        for f in tables.facts
        if f.table_id == "T4.16" and f.field == "display_priority"
    }
    assert (priority["P1"], priority["P2"], priority["P3"]) == ("1", "2", "2")
    units = {
        f.period: f.text
        for f in tables.facts
        if f.table_id == "operating-kpis" and f.field == "unit"
    }
    assert (units["P1"], units["P2"]) == ("USD", "EUR")
    values = {
        f.period: f.unit
        for f in tables.facts
        if f.table_id == "operating-kpis" and f.field == "value"
    }
    assert (values["P1"], values["P2"]) == ("USD", "EUR")


def test_a_readiness_finding_names_its_code_quarter_and_references() -> None:
    finding = ReadinessFinding(
        code="missing_checks",
        severity="BLOCK",
        construction_id="q2",
        references=("CFO_IDENTITY", "NCF_IDENTITY"),
        explanation="Mandatory reconciliation types are absent: CFO_IDENTITY, NCF_IDENTITY",
    )
    assert _finding_text(finding) == (
        "BLOCK missing_checks (q2) [CFO_IDENTITY, NCF_IDENTITY]: "
        "Mandatory reconciliation types are absent: CFO_IDENTITY, NCF_IDENTITY"
    )
    bare = ReadinessFinding(code="quarter_count", severity="BLOCK", explanation="Four needed")
    assert _finding_text(bare) == "BLOCK quarter_count: Four needed"
