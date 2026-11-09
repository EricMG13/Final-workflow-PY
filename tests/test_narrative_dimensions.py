"""CP-1 narrative scope per financial dimension (ruling S13-vii-canonical-context-A07).

Expected values are hand-derived from the ruling, not from the code under test: leverage and
coverage are in scope only with an available ratio KPI of their own kind (a leverage multiple,
a coverage multiple); liquidity only with an available value KPI among cash_closing, liquidity,
undrawn_rcf, total_debt; cash_flow_quality only with fcf, ffo or cfo_adjusted. A bare revenue
value, an unavailable amount or a ratio of another family supports none of them; a zero amount is
an available amount (missing is not zero).

The end-to-end cases build the real narrative inputs of the frozen financial fixture
(tests/test_financial_workflow.py helpers, no store and no CP-0/CP-1 promotion), where every
supporting KPI is available, then withdraw the amounts of the KPIs a case names.
"""

import json
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii import narrative
from deploy_vii.canonical_kpis import CanonicalKpi
from deploy_vii.cp1_workflow import FinancialSubmission
from deploy_vii.financial_model import MetricLeg
from deploy_vii.financial_periods import PeriodValue
from deploy_vii.live.context import narrative_evidence
from deploy_vii.live.submission import PHASES, Known, prefill
from deploy_vii.narrative import NarrativeInputs, NarrativeReview, financial_dimensions
from deploy_vii.source_context import SourceContextReview

LEG = MetricLeg(amount=None, operands=())


def _kpi(operation: str, key: str, amount: str | None = "1.5") -> CanonicalKpi:
    return CanonicalKpi(
        calculation_id=f"kpi-{operation}-{key}",
        display_basis_id="basis-fy2025",
        period_basis_id="basis-fy2025",
        key=key,
        operation=operation,  # type: ignore[arg-type]
        unit="MULTIPLE" if operation == "ratio" else "MILLIONS",
        currency="USD",
        input_scale="MILLIONS",
        formula=key,
        numerator=LEG,
        denominator=None,
        value=PeriodValue(
            amount=None if amount is None else Decimal(amount),
            stated_amount=None,
            value_class="calculated",
            calculation_status="Calculated" if amount else "Not Available",
            reason=None if amount else "NOT_SOURCED",
            note=None,
            observation_ids=(),
            issuance_facility_ids=(),
            citations=(),
        ),
    )


def _ledger(*kpis: CanonicalKpi | None) -> SimpleNamespace:
    """Only `ledger.kpis.kpis` is read; None stands for a ledger with no KPI report."""
    return SimpleNamespace(kpis=None if kpis == (None,) else SimpleNamespace(kpis=kpis))


@pytest.mark.parametrize(
    ("kpis", "want"),
    [
        # no KPI report at all, and a pack with only a revenue figure: none in scope
        ((None,), ()),
        ((_kpi("value", "revenue", "100"),), ()),
        # the revenue figure beside every unavailable ratio: still none
        (
            (
                _kpi("value", "revenue", "100"),
                _kpi("ratio", "total_leverage_reported", None),
                _kpi("ratio", "interest_coverage_reported", None),
            ),
            (),
        ),
        # only a leverage ratio (net leverage adjusted): leverage alone
        ((_kpi("value", "revenue", "100"), _kpi("ratio", "net_leverage_adjusted")), ("leverage",)),
        # only a coverage ratio: coverage alone
        ((_kpi("ratio", "ffo_interest_coverage"),), ("coverage",)),
        # only cash values: liquidity from cash_closing, nothing for cash flow
        ((_kpi("value", "cash_closing", "40"),), ("liquidity",)),
        ((_kpi("value", "total_debt", "900"),), ("liquidity",)),
        # cash-flow values: fcf alone supports cash_flow_quality
        ((_kpi("value", "fcf", "-3"),), ("cash_flow_quality",)),
        ((_kpi("value", "cfo_adjusted", "12"),), ("cash_flow_quality",)),
        # a ratio of another family (fcf_to_debt, liquidity_to_debt) supports neither dimension
        ((_kpi("ratio", "fcf_to_debt"), _kpi("ratio", "liquidity_to_debt")), ()),
        # a value row named like a ratio, or a ratio named like a value, is the wrong operation
        ((_kpi("value", "total_leverage_reported"), _kpi("ratio", "cash_closing")), ()),
        # growth rows of a supporting key do not count
        ((_kpi("growth", "fcf_growth"),), ()),
        # review: an "unavailable" row of a supporting key does not count; a zero amount does
        ((_kpi("unavailable", "fcf"),), ()),
        ((_kpi("value", "total_debt", "0"),), ("liquidity",)),
        ((_kpi("ratio", "net_leverage_reported", "0"),), ("leverage",)),
        # all of them, in dimension order
        (
            (
                _kpi("value", "liquidity", "75"),
                _kpi("value", "ffo", "10"),
                _kpi("ratio", "interest_coverage_adjusted"),
                _kpi("ratio", "senior_secured_leverage"),
            ),
            ("leverage", "coverage", "cash_flow_quality", "liquidity"),
        ),
    ],
)
def test_dimensions_follow_their_supporting_kpis(
    kpis: tuple[CanonicalKpi | None, ...], want: tuple[str, ...]
) -> None:
    assert financial_dimensions(_ledger(*kpis)) == want  # type: ignore[arg-type]


# --- end to end over the frozen financial fixture (review of the ruling) -----------------------
LEVERAGE = (
    "total_leverage_reported",
    "total_leverage_adjusted",
    "net_leverage_reported",
    "net_leverage_adjusted",
    "senior_secured_leverage",
    "senior_secured_leverage_reported",
)
COVERAGE = (
    "interest_coverage_reported",
    "interest_coverage_adjusted",
    "capex_adjusted_coverage",
    "capex_adjusted_coverage_reported",
    "ffo_interest_coverage",
)
LIQUIDITY = ("cash_closing", "liquidity", "undrawn_rcf", "total_debt")
CASH_FLOW = ("fcf", "ffo", "cfo_adjusted")
FINANCIAL = ("leverage", "coverage", "cash_flow_quality", "liquidity")


@pytest.fixture(scope="module")
def case() -> SimpleNamespace:
    import test_financial_workflow as fx

    pack = fx.make_pack()
    kinds = frozenset().union(*PHASES)
    sources = {s.source_id: s.sha256 for s in pack.sources if s.status == "ready" and s.sha256}
    raw = fx.context(pack)
    raw = raw if isinstance(raw, str) else json.dumps(raw)
    known = Known(pack.content_hash(), sources, {})
    context = SourceContextReview.model_validate_json(
        prefill(SourceContextReview, raw, known, kinds).payload
    )
    known = Known(
        pack.content_hash(),
        sources,
        {"context-step": "0" * 64, "source-context-review": context.content_hash()},
        context,
    )
    payload = prefill(FinancialSubmission, json.dumps(fx.financials(pack)), known, kinds).payload
    sub = FinancialSubmission.model_validate_json(payload)
    args = (pack, context, sub.financial, sub.definition, sub.binding)
    inputs = narrative.narrative_inputs(*args)
    stage = SimpleNamespace(narrative_inputs=inputs, model=None)
    return SimpleNamespace(
        args=args,
        inputs=inputs,
        review=fx.narrative({"body": narrative_evidence(stage)}),  # type: ignore[arg-type]
        limitation=fx.LIMIT,
    )


def _withdrawn(inputs: NarrativeInputs, keys: tuple[str, ...], scope: str) -> NarrativeInputs:
    """`inputs` with every period's amount of the named KPIs withdrawn, and the stated scope."""
    kpis = inputs.ledger.kpis
    assert kpis is not None and keys
    gone = {"amount": None, "calculation_status": "Not Available", "reason": "NOT_SOURCED"}
    rows = tuple(
        k.model_copy(update={"value": k.value.model_copy(update=gone)}) if k.key in keys else k
        for k in kpis.kpis
    )
    assert sum(k.key in keys for k in rows) >= len(keys)
    ledger = inputs.ledger.model_copy(update={"kpis": kpis.model_copy(update={"kpis": rows})})
    return NarrativeInputs.model_validate_json(
        NarrativeInputs.model_construct(
            ledger=ledger,
            catalogue=narrative._catalogue(ledger),
            scope=scope,  # type: ignore[arg-type]
        ).model_dump_json()
    )


def _review(case: SimpleNamespace, inputs: NarrativeInputs, drop: tuple[str, ...]) -> Any:
    """The fixture's review bound to `inputs`, without the findings of the `drop` dimensions
    (their coverage then reads unassessed with no findings)."""
    review = json.loads(json.dumps(case.review))
    review["inputs_sha256"] = inputs.content_hash()
    review["findings"] = [f for f in review["findings"] if f["dimension"] not in drop]
    for entry in review["coverage"]:
        if entry["dimension"] in drop:
            entry.update(status="unassessed", finding_ids=[])
    return NarrativeReview.model_validate_json(json.dumps(review))


def _narrative_gaps(
    case: SimpleNamespace, inputs: NarrativeInputs, review: Any, monkeypatch: pytest.MonkeyPatch
) -> tuple[str, list[tuple[str, str]]]:
    monkeypatch.setattr(narrative, "narrative_inputs", lambda *_: inputs)
    report = narrative.canonical_narrative(*case.args, review)
    own = [(g.reference, g.description) for g in report.gaps if g.origin == "narrative"]
    return report.status, own


def test_the_frozen_fixture_supports_every_dimension_and_validates(case: SimpleNamespace) -> None:
    """Every supporting KPI of the fixture has an amount: all four dimensions, no issue."""
    assert case.inputs.scope == "financial_synthesis"
    assert financial_dimensions(case.inputs.ledger) == FINANCIAL
    review = _review(case, case.inputs, ())
    assert narrative.validate_narrative_review(case.inputs, review) == ()


def test_a_leverage_finding_without_a_leverage_ratio_is_refused(
    case: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No leverage ratio: the scope stays financial_synthesis (three dimensions remain), the
    leverage finding is refused, and once withdrawn the narrative records the per-dimension gap
    instead of an "unassessed" one, with no data-quality-only gap."""
    inputs = _withdrawn(case.inputs, LEVERAGE, "financial_synthesis")
    assert financial_dimensions(inputs.ledger) == ("coverage", "cash_flow_quality", "liquidity")
    assert narrative.validate_narrative_review(inputs, _review(case, inputs, ())) == (
        "Financial narrative requires an available leverage KPI: leverage",
    )
    repaired = _review(case, inputs, ("leverage",))
    assert narrative.validate_narrative_review(inputs, repaired) == ()
    assert _narrative_gaps(case, inputs, repaired, monkeypatch) == (
        "restricted",
        [
            ("leverage", "No available KPI supports the leverage dimension"),
            ("limitation:0", case.limitation),
        ],
    )


def test_no_supporting_kpi_limits_the_narrative_to_data_quality(
    case: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Revenue and the other values stay, every supporting KPI goes: data_quality_only, each
    financial finding refused in finding order, a stale financial_synthesis scope refused whole,
    and the repaired review gets the single data-quality gap and no per-dimension gap."""
    keys = (*LEVERAGE, *COVERAGE, *LIQUIDITY, *CASH_FLOW)
    stale = _withdrawn(case.inputs, keys, "financial_synthesis")
    assert narrative.validate_narrative_review(stale, _review(case, stale, ())) == (
        "Narrative scope differs from available KPI evidence",
    )
    inputs = _withdrawn(case.inputs, keys, "data_quality_only")
    assert financial_dimensions(inputs.ledger) == ()
    assert narrative.validate_narrative_review(inputs, _review(case, inputs, ())) == tuple(
        f"Financial narrative requires an available {d} KPI: {d}" for d in FINANCIAL
    )
    repaired = _review(case, inputs, FINANCIAL)
    assert narrative.validate_narrative_review(inputs, repaired) == ()
    assert _narrative_gaps(case, inputs, repaired, monkeypatch) == (
        "restricted",
        [
            ("financial-synthesis", "No available KPI: narrative is limited to data quality"),
            ("limitation:0", case.limitation),
        ],
    )


def test_one_remaining_value_kpi_keeps_its_dimension_alone(case: SimpleNamespace) -> None:
    """Only total_debt left among the supporting KPIs: liquidity alone; a cash-flow finding is
    refused, the liquidity finding is not."""
    keys = (*LEVERAGE, *COVERAGE, "cash_closing", "liquidity", "undrawn_rcf", *CASH_FLOW)
    inputs = _withdrawn(case.inputs, keys, "financial_synthesis")
    assert financial_dimensions(inputs.ledger) == ("liquidity",)
    review = _review(case, inputs, ("leverage", "coverage"))
    assert narrative.validate_narrative_review(inputs, review) == (
        "Financial narrative requires an available cash_flow_quality KPI: cash_flow_quality",
    )
