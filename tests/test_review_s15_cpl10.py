"""S15 review regressions for CP-L10: the money basis of the plain Upstream, the all-missing scope
row, and the analyst texts the claim and the limitations show as written.

Expected texts are literals written here; inputs are the oracle's CP-1 operands and its positive
submission with one stated edit each (synthetic regressions, not a live run).
"""

import copy
import json
import re
from decimal import Decimal
from typing import Any

import pytest
import test_method_cpl10 as method

from deploy_vii.contracts import Fact
from deploy_workflow.owners import cpl10, period_basis

Q1_EBITDA = "Q1 25 (2025-01-01 to 2025-03-31) · ebitda"


def _money(update: dict[str, Any], label: str | None = None) -> list[Fact]:
    """The oracle operands with ``update`` on the known money operands (all, or one label)."""
    return [
        f.model_copy(update=update)
        if f.unit == "MILLIONS" and f.status == "known" and label in (None, f.label)
        else f
        for f in method._cp1_facts()
    ]


def test_the_plain_upstream_refuses_eur_money_operands() -> None:
    """Before: EUR operands were screened and the derived cells and claims said USD."""
    with pytest.raises(
        cpl10.UpstreamError,
        match="^" + re.escape(f"CP-1 operand currency EUR is not USD: {Q1_EBITDA}") + "$",
    ):
        method._upstream(_money({"currency": "EUR"}))


def test_the_plain_upstream_refuses_one_quarter_in_another_currency() -> None:
    with pytest.raises(cpl10.UpstreamError, match="operand currency GBP is not USD"):
        method._upstream(_money({"currency": "GBP"}, Q1_EBITDA))


def test_money_operands_must_be_at_the_million_scale_of_the_derived_cells() -> None:
    """Before: CP-1 money at scale 1 was copied at scale 1 beside a change cell at 1,000,000."""
    with pytest.raises(cpl10.UpstreamError, match="^CP-1 operand scale 1 is not 1000000: "):
        method._upstream(_money({"scale": Decimal(1)}))


def test_a_eur_run_upstream_still_labels_eur() -> None:
    fields = {f: getattr(method.UPSTREAM, f) for f in method.UPSTREAM.__dataclass_fields__}
    eur = cpl10.bind_operands(_money({"currency": "EUR"}))
    up = cpl10.RunUpstream(
        **{**fields, "cp1_facts": eur},
        run_currency=period_basis.currency_of("EUR"),
    )
    assert [t.token for t in up.topics][:2] == ["EUR m", "EUR m"]


def test_the_usd_oracle_upstream_is_unchanged() -> None:
    assert method._upstream().currency.currency == "USD"


def test_no_topic_with_complete_evidence_is_stated_none() -> None:
    """Before: TL10.1.cp1.topics_supported was a known fact with empty text."""
    facts = [
        Fact.model_validate(
            {**f.model_dump(), "status": "missing", "amount": None, "limitation": "Not stated"}
        )
        for f in method._cp1_facts()
    ]
    up = method._upstream(facts)
    sub = copy.deepcopy(method.SUBMISSIONS["positive"])
    sub["assessments"] = []
    assert method._issues(sub, up) == []
    result = cpl10.change_screen(submission=json.dumps(sub), upstream=up)
    cell = {c.fact.fact_id: c.fact for c in result.cells}["TL10.1.cp1.topics_supported"]
    assert (cell.status, cell.text) == (
        "known",
        "None: no topic has a CP-1 known value at both quarters compared",
    )


def _insufficient(limitation: str) -> dict[str, Any]:
    sub = copy.deepcopy(method.SUBMISSIONS["positive"])
    sub["overall"].update(
        category="Insufficient Information",
        confidence="Insufficient Information",
        limitation=limitation,
    )
    return sub


def test_the_overall_limitation_holds_no_figure_and_no_conclusion() -> None:
    """Before: the limitation was not checked and reached the claim verbatim."""
    sub = _insufficient("EBITDA fell to US$ 3.2m; we recommend a covenant reset.")
    assert method._issues(sub) == [
        "overall.limitation: must not contain a digit",
        "overall.limitation: prohibited conclusion: recommend",
        "overall.limitation: prohibited conclusion: covenant",
    ]


def test_a_reference_in_the_overall_limitation_is_refused() -> None:
    sub = _insufficient("The change {TL10.2.ebitda.change|US$ m} is not explained.")
    assert method._issues(sub) == ["overall.limitation: must not contain a digit"]


def test_a_plain_overall_limitation_is_accepted() -> None:
    assert method._issues(_insufficient("The comparison rests on two quarters only.")) == []


def test_gap_texts_hold_no_prohibited_conclusion() -> None:
    sub = copy.deepcopy(method.SUBMISSIONS["positive"])
    sub["gaps"][0]["gap"] = "We recommend a covenant waiver because recovery is unlikely."
    sub["gaps"][0]["why_it_matters"] = "Recommend refinancing now."
    sub["gaps"][0]["action"] = "Check the covenant package."
    assert method._issues(sub) == [
        "gaps[0].gap: prohibited conclusion: recommend",
        "gaps[0].gap: prohibited conclusion: recovery",
        "gaps[0].gap: prohibited conclusion: covenant",
        "gaps[0].why_it_matters: prohibited conclusion: recommend",
        "gaps[0].action: prohibited conclusion: covenant",
    ]
