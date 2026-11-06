"""S05 review: CP-6's recommendation basis rule (methods/cp6.md, the CP-5 rule). A call that
is not Insufficient Information rests on a CP-2 or CP-3 claim row CP-5 does not flag, or on a
CP-1 figure in its rationale or conditions; the CP-5 flag test is on the claim rows. The
refusal names exactly that rule."""

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from deploy_vii.contracts import Fact
from deploy_vii.cp6_committee import Basis, Recommendation, _support_issues

_FIGURE = Fact(
    fact_id="T4.10.net_leverage.fy2024",
    label="Net leverage",
    table_id="T4.10",
    row_id="net_leverage",
    field="fy2024",
    amount=Decimal("3.2"),
    unit="MULTIPLE",
    period="FY2024",
    calculation_id="calc-net-leverage",
)
_BOUND = {_FIGURE.fact_id: _FIGURE}
_UPSTREAM: Any = SimpleNamespace(
    claim_rows={("CP-2", "T2.7.thesis"): "claim", ("CP-3", "T3.4.preference"): "claim"},
    review=SimpleNamespace(flagged=frozenset({("CP-2", "T2.7.thesis")})),
)


def _call(rationale: str, cp2: tuple[str, ...] = (), cp3: tuple[str, ...] = ()) -> Recommendation:
    return Recommendation(
        action_bias="Neutral",
        rationale=rationale,
        conditions="A change in the operating trend",
        confidence="Medium",
        limitation=None,
        basis=Basis(cp2_refs=cp2, cp3_refs=cp3, cp5_refs=()),
    )


def test_no_support_names_the_documented_rule() -> None:
    refusal = (
        "recommendation.basis: cites no CP-2 or CP-3 claim row CP-5 leaves unflagged and no "
        "CP-1 figure in its rationale or conditions"
    )
    assert _support_issues(_call("Stable credit"), _UPSTREAM, _BOUND) == [refusal]


def test_only_flagged_rows_are_refused() -> None:
    issues = _support_issues(_call("Stable credit", cp2=("T2.7.thesis",)), _UPSTREAM, _BOUND)
    assert issues == ["recommendation.basis: rests only on CP-5-flagged claims (CP-2 T2.7.thesis)"]


def test_an_unflagged_row_or_a_cp1_figure_supports_the_call() -> None:
    assert _support_issues(_call("Stable", cp3=("T3.4.preference",)), _UPSTREAM, _BOUND) == []
    figure = "Leverage of {T4.10.net_leverage.fy2024|x} is stable"
    assert _support_issues(_call(figure, cp2=("T2.7.thesis",)), _UPSTREAM, _BOUND) == []
