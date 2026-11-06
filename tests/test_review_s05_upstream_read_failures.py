"""S05 review: a CP-4 or CP-6 step whose bound upstream head cannot be read (a missing or
tampered result blob) is a validator issue, so the attempt is rejected through the repair and
blocked path, as CP-5's `review_scope` does; the ValueError never escapes the validator."""

from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii import cp4_legal, cp6_committee
from deploy_vii.contracts import Input
from deploy_vii.cp4_legal import CovenantInterpretationSubmission, ProtectionScore
from deploy_vii.cp6_committee import Basis, CommitteeSubmission, Recommendation
from deploy_vii.execution import Attempt, StepSubmission, text_sha256

_MISSING = "Execution blob " + "c" * 64 + " is missing"


class _Store:
    """Serves the retained payload; every bound result blob is missing."""

    def __init__(self, payload: str) -> None:
        self._payload = payload

    def payload(self, sha256: str) -> str:
        assert sha256 == text_sha256(self._payload)
        return self._payload

    def pack(self, *_: object) -> object:
        return SimpleNamespace(sources=())

    def read(self) -> object:
        return SimpleNamespace(heads=())

    def result(self, sha256: str) -> object:
        raise ValueError(_MISSING)


def _attempt(module_id: str, step_id: str, payload: str, bound: tuple[str, ...]) -> Attempt:
    inputs = tuple(Input(input_id=m, sha256="c" * 64) for m in bound)
    step = StepSubmission(step_id=step_id, inputs=inputs, payload_sha256=text_sha256(payload))
    return Attempt(ticket_id="t1", module_id=module_id, inputs=inputs, number=0, steps=(step,))


def test_cp4_rejects_an_unreadable_cp1_head() -> None:
    payload = CovenantInterpretationSubmission(
        documents=(),
        covenants=(),
        capacity=(),
        red_flags=(),
        protection_score=ProtectionScore(
            rating="Insufficient Information",
            rationale="r",
            basis="b",
            citations=(),
            limitation=None,
        ),
        gaps=(),
    ).model_dump_json()
    store: Any = _Store(payload)
    attempt = _attempt("CP-4", cp4_legal.STEP_ID, payload, ("CP-0", "CP-1"))
    outcome = cp4_legal._validate_step(store, store.pack(), attempt)
    assert outcome.output is None
    assert outcome.issues == (f"Unreadable upstream heads: {_MISSING}",)


def test_cp6_rejects_an_unreadable_bound_head(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cp6_committee, "current_inputs", lambda snapshot, module_id: ())
    basis = Basis(cp2_refs=(), cp3_refs=(), cp5_refs=())
    payload = CommitteeSubmission(
        recommendation=Recommendation(
            action_bias="Insufficient Information",
            rationale="r",
            conditions="c",
            confidence="Insufficient Information",
            limitation=None,
            basis=basis,
        ),
        thesis_challenges=(),
        recovery_view=(),
        risks=(),
        gaps=(),
    ).model_dump_json()
    store: Any = _Store(payload)
    attempt = _attempt(
        "CP-6", cp6_committee.STEP_ID, payload, ("CP-0", "CP-1", "CP-2", "CP-3", "CP-5")
    )
    outcome = cp6_committee._validate_step(store, store.pack(), attempt)
    assert outcome.output is None
    assert outcome.issues == (f"Unreadable upstream heads: {_MISSING}",)
