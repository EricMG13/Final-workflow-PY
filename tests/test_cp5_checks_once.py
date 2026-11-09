"""S09-C06: one CP-5 compute, owner view and step validation runs `python_checks` once."""

from collections import Counter

import pytest
from test_method_cp5 import make_inputs

from deploy_vii import cp5_integrity
from deploy_workflow.owners import cp5


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> Counter[str]:
    counter: Counter[str] = Counter()
    real = cp5_integrity.python_checks

    def counted(scope: cp5_integrity.ReviewScope) -> cp5_integrity.PythonChecks:
        counter["python_checks"] += 1
        return real(scope)

    monkeypatch.setattr(cp5_integrity, "python_checks", counted)
    monkeypatch.setattr(cp5, "python_checks", counted)
    return counter


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_compute_and_the_owner_view_run_the_checks_once(case: str, calls: Counter[str]) -> None:
    inputs = make_inputs(case)
    result = cp5.compute(inputs)
    assert result.report is not None and not result.issues
    assert calls["python_checks"] == 1  # was 3: validate, validate again inside compose, compose
    calls.clear()
    cp5.view_body(inputs.scope)
    assert calls["python_checks"] == 1  # was 3: projection, context block, findings


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_outcome_equals_validate_then_compose(case: str) -> None:
    # The single-pass path gives exactly what the two public calls give.
    inputs = make_inputs(case)
    issues, report = cp5_integrity.review_outcome(inputs.scope, inputs.submission)
    assert issues == cp5_integrity.validate_integrity(inputs.scope, inputs.submission) == ()
    assert report == cp5_integrity.integrity_review(inputs.scope, inputs.submission)
