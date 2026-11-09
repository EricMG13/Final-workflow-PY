"""S16 A05/C09: a row is a total row by construction (the TDR.3 sum row), not by its id."""

import copy
import json
from pathlib import Path

import pytest
from cpdr_o7b1b_support import brief, evidence
from cpdr_peers_support import peers_case

from deploy_vii.contracts import validate_tables
from deploy_workflow.research import review
from deploy_workflow.research import tables as t

CASE = Path(__file__).resolve().parents[2] / "cases" / "cpdr-research-owner"


def _total_rows(composed: t.Composed) -> list[tuple[str, str]]:
    return [
        (x.table_id, r.row_id) for x in composed.tables for r in x.rows if r.row_kind == "total"
    ]


# " total " fails the Identifier pattern at parse, so it never reaches composition.
@pytest.mark.parametrize("claim_id", ["total", "TOTAL"])
def test_a_claim_named_total_is_an_ordinary_row(claim_id: str) -> None:
    exp = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))
    subs = json.loads((CASE / "submissions.json").read_text(encoding="utf-8"))
    body = copy.deepcopy(subs["research_v1"])
    next(a for a in body["answers"] if a["claims"])["claims"][0]["claim_id"] = claim_id
    sub = review.ResearchSubmission.parse(body)
    b, ev = brief(exp, "positive"), evidence(exp)
    composed = t.compose(
        b, sub, ev, review.answer_counts(sub), review.claim_states(sub, b), b.as_of.isoformat()
    )
    validate_tables(composed.tables, composed.facts)
    # Hand-derived: TDR.3 has exactly one sum row and nothing else is a total.
    assert _total_rows(composed) == [("TDR.3", "total")]


@pytest.mark.parametrize("peer_id", ["total", "TOTAL"])
def test_a_peer_named_total_is_an_ordinary_row(peer_id: str) -> None:
    case = peers_case()
    body = json.loads(json.dumps(case.body).replace('"p01"', json.dumps(peer_id)))
    composed = case.composed(body)
    assert [t_ for t_ in _total_rows(composed) if t_[0] == "TDR.4"] == []
    assert any(r.row_id == peer_id for x in composed.tables for r in x.rows)
