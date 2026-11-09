"""S07-cp2-gh-C03: one staleness frame and one gap-row shape for CP-2G, CP-2H and CP-4C.

`stale_issues` was AST-identical in the three modules and `SynthesisGap` had identical fields; the
CP-2H and CP-4C copies are now CP-2G's. Each `SynthesisGap` keeps its own docstring, because it is
the gap row's description in the step's response schema. The expected frame below is hand-written
from the rule (ruling 10): a refusal text is "Stale inputs: <text>" clipped to the issue limit,
and each changed bound input is "Stale input <id>: bound <status> <sha[:12]>, current ...".
"""

from types import ModuleType

import pytest

from deploy_vii.contracts import Input
from deploy_vii.execution import MAX_ISSUE_CHARS
from deploy_vii.live.schema import strict_copy
from deploy_workflow.owners import cp2g, cp2h, cp4c

A, B = "a" * 64, "b" * 64


@pytest.mark.parametrize("module", [cp2h, cp4c])
def test_stale_issues_is_cp2gs(module: ModuleType) -> None:
    assert module.stale_issues is cp2g.stale_issues


def test_the_shared_frame() -> None:
    bound = (Input(input_id="CP-1", sha256=A, status="accepted"),)
    current = (Input(input_id="CP-1", sha256=B, status="restricted"),)
    assert cp2h.stale_issues(bound=bound, current=current) == (
        "Stale input CP-1: bound accepted aaaaaaaaaaaa, current restricted bbbbbbbbbbbb",
    )
    assert cp4c.stale_issues(bound=bound, current=()) == (
        "Stale input CP-1: bound accepted aaaaaaaaaaaa, current absent",
    )
    (clipped,) = cp2h.stale_issues(bound=bound, current="x" * 5000)
    assert clipped.startswith("Stale inputs: xxx") and len(clipped) <= MAX_ISSUE_CHARS


@pytest.mark.parametrize(
    ("module", "description"),
    [
        (cp2h, "As the CP-2G `SynthesisGap`."),
        (cp4c, "CP-4C's own gap row: the CP-2G `SynthesisGap` shape (lease)."),
    ],
)
def test_gap_rows_share_cp2gs_fields_and_keep_their_own_description(
    module: ModuleType, description: str
) -> None:
    gap = module.SynthesisGap
    assert issubclass(gap, cp2g.SynthesisGap) and gap is not cp2g.SynthesisGap
    assert "__annotations__" not in vars(gap) or not vars(gap)["__annotations__"]
    assert list(gap.model_fields) == [
        "gap",
        "why_it_matters",
        "affected_analysis",
        "severity",
        "action",
    ]
    submission = cp2h.TriggerSubmission if module is cp2h else cp4c.RestructuringSubmission
    assert strict_copy(submission)["$defs"]["SynthesisGap"]["description"] == description
