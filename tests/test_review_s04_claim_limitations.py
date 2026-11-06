"""Review S04: `Claim.limitation` is plain text, so CP-2 and CP-1A spell a `{ref|unit}` in it
as their tables do (code review cp2_synthesis.py:868, business_context.py:1715).

Synthetic: the S1 snapshot pack and literals with one limitation edited to reference the CP-1
LTM total-leverage fact of the cp3-cp6-owner fixture; `1.67x` is that oracle's spelling.
"""

import json

import s1a_runs
import test_method_cp3 as cp3_fixture

from deploy_vii import business_context, cp2_synthesis
from deploy_vii.contracts import Input, Module

FACT = cp3_fixture.FIGS["total_leverage_reported"]
REF = "{" + FACT.fact_id + "|x}"
SPELLED = cp3_fixture.SUBMISSIONS["figures"]["total_leverage_reported"]["spelled"]


def test_spelled_oracle_value() -> None:
    assert SPELLED == "1.67x"


def test_cp1a_claim_limitation_is_spelled() -> None:
    pack = s1a_runs.make_pack("positive")
    literal = json.loads(s1a_runs.literal("positive", "business_context", pack))
    literal["credit_translations"][0]["limitation"] = f"Read beside leverage of {REF}"
    submission = business_context.BusinessContextSubmission.model_validate_json(json.dumps(literal))
    report = business_context.business_context(pack, submission, (FACT,))
    claim = next(c for c in report.claims if c.claim_id == "credit_translation.r01")
    assert claim.limitation == "Read beside leverage of 1.67x"


def test_cp2_claim_limitation_is_spelled() -> None:
    pack = s1a_runs.make_pack("positive")
    plain = "The supplied record gives no further basis for a view."
    syn = cp2_synthesis
    submission = syn.CreditSynthesisSubmission(
        assessment=syn.Assessment(
            rationale=plain,
            category="Insufficient Information",
            confidence="Low",
            cp1a_refs=(),
            limitation=f"No maturity split at leverage of {REF}",
        ),
        thesis=syn.Thesis(
            text=plain, category="Insufficient Information", cp1a_refs=(), limitation=plain
        ),
        strengths=(),
        weaknesses=(),
        key_findings=(),
        risks=(),
        gaps=(),
    )

    def module(module_id: str, facts: tuple = ()) -> Module:  # type: ignore[type-arg]
        return Module(
            run_id=pack.run.run_id,
            issuer_id=pack.run.issuer_id,
            as_of=pack.run.as_of,
            module_id=module_id,
            facts=facts,
        )

    cp1, cp1a = module("CP-1", (FACT,)), module("CP-1A")
    bound = tuple(
        Input(input_id=m.module_id, sha256=m.content_hash(), status="restricted")
        for m in (cp1, cp1a)
    )
    upstream = syn.Upstream(bound=bound, current=bound, cp1=cp1, cp1a=cp1a, inherited=())
    report = syn.credit_synthesis(pack, submission, upstream)
    claim = next(c for c in report.claims if c.claim_id == "T2.1.assessment")
    assert claim.limitation == "No maturity split at leverage of 1.67x"
