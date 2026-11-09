"""S09-C03: the CP-4 context note names no facility only when no facility is listed."""

from types import SimpleNamespace

from deploy_vii.cp4_legal import Upstream, context_block

SHA = "0" * 64


def _note(*, facilities: dict[str, str], facts: tuple[object, ...] = ()) -> str:
    up = Upstream(
        cp0_sha256=SHA,
        cp1_sha256=SHA,
        cp1_status="restricted",
        authority={},
        legal_sources=(),
        facilities=facilities,
        facts=facts,  # type: ignore[arg-type]
        rows={},
        cp1_gaps=(),
    )
    block = context_block(SimpleNamespace(sources=()), up)  # type: ignore[arg-type]
    assert [f["facility_id"] for f in block["facilities"]] == list(facilities)
    return str(block["cp1_facts_note"])


def test_no_figure_and_no_facility_says_both() -> None:
    assert _note(facilities={}) == (
        "No CP-1 figure is offered: write no figure, name no metric_ref and no facility."
    )


def test_no_figure_but_a_listed_facility_does_not_forbid_naming_it() -> None:
    # Hand-derived: the facility is listed in the same block and the validator accepts its id,
    # so the note forbids only the figure and the metric_ref.
    note = _note(facilities={"term-loan": "Senior secured term loan"})
    assert note == "No CP-1 figure is offered: write no figure and name no metric_ref."
    assert "facility" not in note


# S09-C05: T4F.3's Result is the headroom in T4.9's unit. Hand-derived with Decimal arithmetic:
# a "not less than 12.5%" covenant (operand 0.125) against a CP-1 fraction.
def _traced(unit: str, comparison: str, operand: str, metric: str) -> str:
    from decimal import Decimal

    from deploy_vii import cp4_legal

    result = cp4_legal.headroom(Decimal(operand), comparison, Decimal(metric))  # type: ignore[arg-type]
    row = SimpleNamespace(threshold_unit=unit, comparison=comparison)
    test = SimpleNamespace(row=row, result=result, reason=None, inapplicable=False)
    return cp4_legal._traced_result(test)  # type: ignore[arg-type]


def test_a_percent_headroom_is_traced_in_percentage_points_like_t49() -> None:
    assert _traced("percent", ">=", "0.125", "0.15") == "2.500 pp"  # 0.025 x 100
    assert _traced("percent", ">=", "0.125", "0.125") == "0.000 pp"  # at the threshold: zero
    assert _traced("percent", ">=", "0.125", "1.0") == "87.500 pp"  # a metric of 100%
    assert _traced("percent", ">=", "0.125", "1.5") == "137.500 pp"  # above 100%
    assert _traced("percent", "<=", "0.5", "0.35") == "15.00 pp"  # an upper limit: 0.15 x 100


def test_a_ratio_headroom_keeps_its_own_amount() -> None:
    assert _traced("x", "<=", "4.00", "1.00") == "3.00"
    assert _traced("x", "<=", "4.00", "4.00") == "0.00"
    assert _traced("x", "<=", "4.00", "5.00") == "-1.00"
