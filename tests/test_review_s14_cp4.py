"""S14 review fix for CP-4's semantic gate: only ready sources are evidence (cr S14 cp4.py:46)."""

import test_method_cp4 as t

from deploy_workflow.owners import cp4

REFUSAL = (
    "covenants[0]: metric_basis 'Same definition' is refused because the cited source text "
    "matches incorporation-by-reference markers: 'has the meaning assigned in'; "
    "'is not supplied with this copy'"
)


def _without_marker_quote(case: str) -> tuple[object, object]:
    inputs = t.make_inputs_object(case)
    (covenant,) = inputs.submission.covenants
    marker = t._marker_quote(covenant)
    kept = tuple(q for q in covenant.citations if q is not marker)
    variant = inputs.submission.model_copy(
        update={"covenants": (covenant.model_copy(update={"citations": kept}),)}
    )
    return inputs, variant


def test_a_ready_cited_page_still_refuses_with_its_markers() -> None:
    inputs, variant = _without_marker_quote("gap_false_same_definition")
    assert cp4.semantic_issues(pack=inputs.pack, submission=variant) == (REFUSAL,)


def test_a_cited_page_of_a_source_that_is_not_ready_is_not_scanned() -> None:
    inputs, variant = _without_marker_quote("gap_false_same_definition")
    sources = tuple(
        s.model_copy(update={"status": "unreadable", "limitation": "Unreadable copy"})
        if s.source_id == "legal-covenants"
        else s
        for s in inputs.pack.sources
    )
    pack = inputs.pack.model_copy(update={"sources": sources})
    assert cp4.semantic_issues(pack=pack, submission=variant) == ()
