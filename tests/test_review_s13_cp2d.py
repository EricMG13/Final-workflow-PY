"""Review S13: CP-2D regressions (T4.18 term status, the minimum-cash judgment text, the
"funding gap on cash alone" limitation). Expected texts and amounts are literals."""

from dataclasses import replace
from decimal import Decimal

from test_method_cp2d import _base_loan, _cells, _inputs, _operands

from deploy_vii.contracts import Fact
from deploy_workflow.owners import cp2d

_WHY = "Two sources disagree on the principal"


def _with_loan(case: str, loan: cp2d.Facility) -> cp2d.Cp2dInputs:
    inputs = _inputs(case)
    return replace(inputs, operands=replace(inputs.operands, facilities=(loan,)))


# --- a T4.18 term CP-1 reports conflicting keeps CP-1's status (adversarial medium, :2163) ----
def _t418(field: str, **values: object) -> Fact:
    base: dict[str, object] = {
        "fact_id": f"cp1.T4.18.r01.{field}",
        "label": field,
        "table_id": "T4.18",
        "row_id": "r01",
        "field": field,
        "period": "q4-2025",
    }
    return Fact.model_validate({**base, **values})


def test_reader_keeps_a_conflicting_principal_status_and_limitation() -> None:
    money = {"unit": "MILLIONS", "currency": "USD", "scale": Decimal(1000000)}
    row = {
        "facility_id": _t418("facility_id", text="tl"),
        "facility_name": _t418("facility_name", text="Term loan"),
        "currency": _t418("currency", text="USD"),
        "principal": _t418("principal", status="conflicting", limitation=_WHY, **money),
        "maturity_date": _t418("maturity_date", text="2026-06-30"),
        "commitment": _t418("commitment", amount=Decimal(50), **money),
        "drawn_amount": _t418("drawn_amount", amount=Decimal(50), **money),
        "annual_amortisation": _t418(
            "annual_amortisation", status="not_applicable", limitation="Bullet loan", **money
        ),
    }
    facility = cp2d._facility_of("tl", row)
    assert facility.principal is None
    assert facility.held("principal") == ("conflicting", _WHY)
    assert facility.held("annual_amortisation") == ("not_applicable", "Bullet loan")
    assert facility.held("commitment") is None
    gap = cp2d._principal(facility)
    assert isinstance(gap, cp2d.OperandGap)
    assert (gap.reason, gap.status, gap.limitation) == (
        "Not calculable: facility tl principal is conflicting",
        "conflicting",
        _WHY,
    )
    amortisation = cp2d._amortisation(facility, 24)
    assert isinstance(amortisation, cp2d.Gap)
    assert (
        amortisation.reason == "Not calculable: facility tl annual amortisation is not applicable"
    )


def test_conflicting_principal_reaches_the_wall_and_the_limitations() -> None:
    loan = replace(_base_loan(), principal=None, unsettled=(("principal", "conflicting", _WHY),))
    result = cp2d.compute(_with_loan("positive", loan))
    cells = _cells(result)
    principal = cells["T2E.4.r01.c1"]
    assert (principal.state, principal.reason) == ("conflicting", _WHY)
    share = cells["T2E.4.r01.c5"]
    assert (share.state, share.reason) == (
        "gap",
        "Not calculable: facility term-loan principal is conflicting",
    )
    assert (
        "Facility term-loan principal is conflicting in CP-1 (Two sources disagree on the "
        "principal); maturity-wall figures that need it are not calculated."
    ) in result.own_limitations
    assert not any("principal is not stated" in t for t in result.own_limitations)


def test_conflicting_maturity_date_cell_keeps_cp1_status() -> None:
    loan = replace(
        _base_loan(),
        maturity_date=None,
        unsettled=(("maturity_date", "conflicting", "The schedules give two dates"),),
    )
    cells = _cells(cp2d.compute(_with_loan("positive", loan)))
    dated = cells["T2E.4.r01.c2"]
    assert (dated.state, dated.reason) == ("conflicting", "The schedules give two dates")
    months = cells["T2E.4.r01.c3"]
    assert months.reason == "Not calculable: facility term-loan maturity date is conflicting"


def test_not_applicable_amortisation_is_named_not_applicable() -> None:
    loan = replace(
        _base_loan(),
        annual_amortisation=None,
        unsettled=(("annual_amortisation", "not_applicable", "Bullet repayment"),),
    )
    result = cp2d.compute(_with_loan("positive", loan))
    cells = _cells(result)
    assert cells["T2E.3.r06"].reason == (
        "Not calculable: facility term-loan annual amortisation is not applicable"
    )
    assert (
        "Facility term-loan annual amortisation is not applicable in CP-1 (Bullet repayment); "
        "maturity-wall figures that need it are not calculated."
    ) in result.own_limitations


def test_conflicting_currency_is_named_conflicting() -> None:
    loan = replace(
        _base_loan(), currency=None, unsettled=(("currency", "conflicting", "USD or EUR"),)
    )
    cells = _cells(cp2d.compute(_with_loan("positive", loan)))
    assert cells["T2E.4.r01.c1"].reason == (
        "Not calculable: facility term-loan currency is conflicting; no FX conversion is applied"
    )
    assert cells["T2E.4.r01.c1"].state == "gap"  # the principal itself is known


def test_missing_principal_keeps_the_not_stated_frame() -> None:
    loan = replace(_base_loan(), principal=None)
    result = cp2d.compute(_with_loan("positive", loan))
    principal = _cells(result)["T2E.4.r01.c1"]
    assert (principal.state, principal.reason) == (
        "gap",
        "Not calculable: facility term-loan principal is not stated",
    )


# --- the minimum-cash judgment text is exact (adversarial low, :1717) -------------------------
def _minimum_text(amount: str) -> str:
    inputs = _inputs("positive")
    assert inputs.submission.minimum_cash is not None
    minimum = inputs.submission.minimum_cash.model_copy(update={"amount": Decimal(amount)})
    submission = inputs.submission.model_copy(update={"minimum_cash": minimum})
    result = cp2d.compute(replace(inputs, submission=submission))
    return dict(result.judgments.rows)["Minimum cash"]


def test_minimum_cash_judgment_is_spelled_exactly() -> None:
    assert _minimum_text("0.4") == "0.4 US$ m (analyst assumption)"
    assert _minimum_text("12.5") == "12.5 US$ m (analyst assumption)"
    assert _minimum_text("10") == "10 US$ m (analyst assumption)"
    assert _minimum_text("10.00") == "10 US$ m (analyst assumption)"


# --- the revolver limitation does not claim a headroom that is a gap (code review, :1012) ------
def test_revolver_limitation_when_cash_only_headroom_is_a_gap() -> None:
    inputs = _inputs("gap_minimum_cash")
    inputs = replace(inputs, operands=_operands("fixture_rcf_undisclosed"))
    result = cp2d.compute(inputs)
    assert _cells(result)["T2E.5.r05"].state == "gap"
    assert (
        "The funding gap is not calculated because the revolver is undisclosed; the cash-only "
        "headroom over minimum cash is not calculated either."
    ) in result.own_limitations
    assert not any("lower bound" in t for t in result.own_limitations)


def test_revolver_limitation_keeps_the_lower_bound_when_headroom_is_known() -> None:
    result = cp2d.compute(
        replace(_inputs("positive"), operands=_operands("fixture_rcf_undisclosed"))
    )
    assert result.own_limitations[-1] == (
        "The funding gap is not calculated because the revolver is undisclosed; the cash-only "
        "headroom over minimum cash is shown as a lower bound."
    )


def test_composed_wall_fact_keeps_cp1_conflicting_principal() -> None:
    """Through the reader and the composer: CP-1 reports the principal conflicting on both the
    quarter row and its FY alias; the T2E.4 principal fact is conflicting with CP-1's limitation
    and cites what the CP-1 fact cites."""
    import test_method_cp2d as tm
    from test_connect_cp2d import cp1_module

    module = cp1_module(tm._base_operands())
    facts = tuple(
        f.model_copy(update={"amount": None, "unit": None, "currency": None, "scale": Decimal(1),
                             "status": "conflicting", "limitation": _WHY})
        if f.table_id == "T4.18" and f.field == "principal"
        else f
        for f in module.facts
    )  # fmt: skip
    selection = cp2d.select_cp1(module.model_copy(update={"facts": facts}))
    inputs = replace(
        _inputs("positive"),
        operands=selection.operands,
        balance_date=selection.balance_date,
        offered_refs=frozenset(o.fact.fact_id for o in selection.offered),
        maturity_date_refs=selection.maturity_date_refs,
    )
    result = cp2d.compute(inputs)
    composer = cp2d._Composer(selection, result)
    for table in result.tables:
        composer.table(table)
    fact = next(f for f in composer.facts if f.fact_id == "T2E.4.r01.c1")
    assert (fact.status, fact.limitation) == ("conflicting", _WHY)
    cp1_principal = selection.facility_fact("term-loan", "principal")
    assert cp1_principal is not None and fact.citations == cp1_principal.citations
