"""S06-cp2-ade-C03 / S10-cp6-cp8-cpl10-C04: a claim's stored limitation spells its figure
references as its table cell does, never as raw `{ref|unit}` braces.

CP-2 (`credit_synthesis`), CP-3 (`relative_value`) and CP-6 (`committee_challenge`) allow figure
references in a limitation and spell them in the table cell; the claim used to keep the raw run
text. Expected values are hand-derived from the fact each test builds: 4.2 MULTIPLE shows as
"4.20x", 120 US$ millions with 0 decimals shows as "120 US$ m", and the fixture's LTM interest
coverage 6 MULTIPLE shows as "6.00x".
"""

import dataclasses
from datetime import date
from decimal import Decimal

import test_engine_blank_text as tb
import test_method_cp3 as t3
import test_method_cp4 as t4

from deploy_vii import cp2_synthesis as cs
from deploy_vii import cp6_committee as c6
from deploy_vii.contracts import Fact, Input, Module, Run
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owners import cp3, cp4


def _cp2_case(
    limitation: str | None,
) -> tuple[PreparedPack, cs.CreditSynthesisSubmission, cs.Upstream]:
    fact = Fact(
        fact_id="T4.10.lev",
        label="Total leverage",
        amount=Decimal("4.2"),
        unit="MULTIPLE",
        period="LTM Q3 2025",
        calculation_id="calc.lev",
    )
    cp1 = tb._module(cs.CP1).model_copy(update={"facts": (fact,)})
    cp1a = tb._module(cs.CP1A)
    inputs = (
        Input(input_id=cs.CP1, sha256=cp1.content_hash()),
        Input(input_id=cs.CP1A, sha256=cp1a.content_hash()),
    )
    upstream = cs.Upstream(bound=inputs, current=inputs, cp1=cp1, cp1a=cp1a, inherited=())
    submission = cs.CreditSynthesisSubmission(
        assessment=cs.Assessment(
            rationale="Credit profile is weak.",
            category="Insufficient Information",
            confidence="Low",
            cp1a_refs=(),
            limitation=limitation,
        ),
        thesis=cs.Thesis(
            text="Thesis text.",
            category="Insufficient Information",
            cp1a_refs=(),
            limitation="No evidence.",
        ),
        strengths=(),
        weaknesses=(),
        key_findings=(cs.Finding(text="Leverage stands at {T4.10.lev|x}.", cp1a_refs=()),),
        risks=(),
        gaps=(),
    )
    return tb._pack(), submission, upstream


def _cp2_report(limitation: str | None) -> cs.CreditSynthesisReport:
    pack, submission, upstream = _cp2_case(limitation)
    assert cs.validate_credit_synthesis(pack, submission, upstream) == ()
    return cs.credit_synthesis(pack, submission, upstream)


def test_cp2_claim_limitation_is_spelled_like_its_cell() -> None:
    report = _cp2_report("Leverage of {T4.10.lev|x} rests on LTM figures only.")
    claim = next(c for c in report.claims if c.claim_id == "T2.1.assessment")
    cell = next(f.text for f in report.facts if f.table_id == "T2.1" and f.field == "limitation")
    assert claim.limitation == "Leverage of 4.20x rests on LTM figures only."
    assert claim.limitation == cell
    # the carried reference table is unchanged: the figure is referenced once
    assert [f.fact_id for f in report.facts if f.table_id == cs.CP1_REFERENCES] == ["T4.10.lev"]


def test_cp2_plain_limitation_is_kept_verbatim() -> None:
    report = _cp2_report("Leverage rests on LTM figures only.")
    claim = next(c for c in report.claims if c.claim_id == "T2.1.assessment")
    assert claim.limitation == "Leverage rests on LTM figures only."


def _cp6_case(limitation: str) -> tuple[PreparedPack, c6.CommitteeSubmission, c6.Upstream]:
    pack = PreparedPack(
        run=Run(
            run_id="run-1",
            issuer_id="acme",
            issuer_name="Acme",
            as_of=date(2026, 1, 1),
            case_kind="synthetic",
        ),
        sources=(),
    )
    fact = Fact(
        fact_id="T4.10.ebitda.fy2025",
        label="EBITDA FY2025",
        table_id="T4.10",
        row_id="ebitda",
        field="fy2025",
        status="known",
        amount=Decimal(120),
        unit="MILLIONS",
        currency="USD",
        scale=Decimal(1000000),
        decimals=0,
        period="FY2025",
        calculation_id="calc-1",
    )

    def module(module_id: str, facts: tuple[Fact, ...] = ()) -> Module:
        return Module(
            run_id="run-1",
            issuer_id="acme",
            as_of=date(2026, 1, 1),
            module_id=module_id,
            facts=facts,
        )

    names = ("CP-0", "CP-1", "CP-2", "CP-3", "CP-5")
    mods = {m: module(m, (fact,) if m == "CP-1" else ()) for m in names}
    inputs = tuple(
        Input(input_id=k, sha256=m.content_hash(), status="accepted") for k, m in mods.items()
    )
    upstream = c6.Upstream(
        bound=inputs,
        current=inputs,
        cp0=mods["CP-0"],
        cp1=mods["CP-1"],
        cp2=mods["CP-2"],
        cp3=mods["CP-3"],
        cp5=mods["CP-5"],
        optional={},
        blocked=frozenset(),
        inherited=(),
    )
    basis = c6.Basis(cp2_refs=(), cp3_refs=(), cp5_refs=())
    submission = c6.CommitteeSubmission(
        recommendation=c6.Recommendation(
            action_bias="Insufficient Information",
            rationale="Market evidence is absent",
            conditions="Obtain a quotation",
            confidence="Insufficient Information",
            limitation=limitation,
            basis=basis,
        ),
        thesis_challenges=(),
        recovery_view=(),
        risks=(),
        gaps=(),
    )
    return pack, submission, upstream


def test_cp6_claim_limitation_is_spelled_like_its_cell() -> None:
    pack, submission, upstream = _cp6_case("CP-1 shows EBITDA of {T4.10.ebitda.fy2025|US$ m} only")
    assert c6.validate_committee(pack, submission, upstream) == ()
    report = c6.committee_challenge(pack, submission, upstream)
    table = next(t for t in report.tables if t.table_id == c6.FINAL_BIAS_TABLE)
    facts = {f.fact_id: f for f in report.facts}
    cell = facts[table.rows[0].fact_ids[-1]].text
    assert report.claims[0].limitation == "CP-1 shows EBITDA of 120 US$ m only" == cell


def test_cp3_claim_limitations_are_spelled_like_their_cells() -> None:
    inputs = t3.make_inputs("positive")
    sub = inputs.submission
    ref = "{T4.10.interest_coverage_reported.ltm_q4_2025|x}"
    preference = sub.preference.model_copy(update={"limitation": f"Cover of {ref} is LTM only"})
    instrument = sub.instruments[0].model_copy(update={"limitation": f"Read with {ref}"})
    sub = sub.model_copy(update={"preference": preference, "instruments": (instrument,)})
    result = cp3.compute(dataclasses.replace(inputs, submission=sub))
    assert result.issues == ()
    assert result.report is not None
    claims = {c.claim_id: c for c in result.report.claims}
    assert claims["T3.4.preference"].limitation == "Cover of 6.00x is LTM only"
    assert claims["T3.1.i01"].limitation == "Read with 6.00x"
    cells = {
        (f.table_id, f.field): f.text
        for f in result.report.facts
        if f.field == "limitation" and f.table_id in ("T3.1", "T3.4")
    }
    assert cells[("T3.4", "limitation")] == "Cover of 6.00x is LTM only"
    assert cells[("T3.1", "limitation")] == "Read with 6.00x"


# CP-4 (`covenant_interpretation`): the fixture's CP-1 net leverage fact is 1.00x (the oracle's
# "spelled" figure, cases/cp4-owner/expected.json). The T4.13 limitation cell spells each
# reference; the "protection_score" claim must store the same text. Expected by hand:
#   two references  -> "Cover 1.00x against 1.00x ok"   (both resolve to the same fact)
#   None -> None in the claim (cell shows "None stated"); empty string and an unknown
#   reference are refused by validation.
def _cp4_report(limitation: str | None) -> cp4.Cp4Result:
    inputs = t4.make_inputs_object("positive")
    ref = t4.select_metric(inputs.pack, inputs.upstream)
    text = limitation.replace("REF", "{" + ref + "|x}") if limitation else limitation
    score = inputs.submission.protection_score
    # a rating above Insufficient Information may carry no limitation, so None and "" can be tried
    cites = inputs.submission.red_flags[0].citations
    score = score.model_copy(update={"limitation": text, "rating": "Adequate", "citations": cites})
    sub = inputs.submission.model_copy(update={"protection_score": score})
    return cp4.compute(
        cp4.Cp4Inputs(
            pack=inputs.pack, submission=sub, upstream=inputs.upstream, inputs=inputs.inputs
        )
    )


def _cp4_claim_and_cell(result: cp4.Cp4Result) -> tuple[str | None, str]:
    assert result.issues == ()
    assert result.report is not None
    claim = next(c for c in result.report.claims if c.claim_id == "protection_score")
    cell = next(
        f.text for f in result.report.facts if f.table_id == "T4.13" and f.field == "limitation"
    )
    return claim.limitation, cell


def test_cp4_claim_limitation_is_spelled_like_its_cell() -> None:
    claim, cell = _cp4_claim_and_cell(_cp4_report("Cover REF against REF ok"))
    assert claim == "Cover 1.00x against 1.00x ok" == cell


def test_cp4_claim_limitation_none_and_empty() -> None:
    claim, cell = _cp4_claim_and_cell(_cp4_report(None))
    assert claim is None
    assert cell == "None stated"
    # an empty string is refused by validation, so it never reaches a claim
    assert _cp4_report("").report is None


def test_cp4_unknown_limitation_reference_is_refused() -> None:
    result = _cp4_report("Cover {no.such.fact|x} ok")
    assert result.report is None
    assert result.issues
