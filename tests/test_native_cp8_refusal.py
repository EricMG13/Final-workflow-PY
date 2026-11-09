"""A native pathway run records a commanded CP-8 as refused (superseded) and finishes.

User ruling: CP-8's decision-ledger post-mortem is superseded (AGENTS.md); a native walk that
reaches a CP-8 the journal would begin retains a refused begin whose reason names the supersession
and the CP-OS comparison route, and the run goes on to its receipt and render as a run with any
refused module does. No CP-8 attempt, request or spend.

Scope: offline and synthetic. The walks are real ``_run_pathway`` walks over the o2 synthetic
case, cut to a CP-0 -> CP-8 plan, with CP-0 answered by the o2 scripted adapter (the frozen
readiness review, CP-8's judgement varied); no provider is called. A full portfolio_decision walk
reaches CP-8 only after CP-1 and the CP-MODEL publication (minutes, ``RUN_PROMOTION``); there CP-8
requires CP-6, so its begin also comes from a submit inside the loop, as here.
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import o2_case
import pytest

from deploy_vii.execution import Execution, current_inputs
from deploy_vii.preparation import PreparationRequest, load_pack
from deploy_workflow import run_pathway as rp
from deploy_workflow.model.adapter import recorded_adapter
from deploy_workflow.model.turn import load_arguments
from deploy_workflow.owner_workflow import (
    AUDIT,
    OWNER_SPECS,
    OwnerRunReceipt,
    OwnerWorkflow,
    RefusedBegin,
    _verify_refusal,
    verify_owner_run_receipt,
)
from deploy_workflow.run_inputs import CheckedRun, RunOutcome, check_arguments, stage_sources
from deploy_workflow.workflow import WorkflowError

# The ruling's text, written out here (never read from the production constant).
SUPERSEDED = (
    "the decision-ledger post-mortem is superseded; compare prior and current deliverables with "
    "CP-OS run_comparison (deploy_workflow.owners.cpos --compare)"
)
REFUSAL = f"native CP-8 is refused: {SUPERSEDED}"  # the typed stop of a CP-8 already begun
NOT_AUTHORIZED = "CP-0 has not authorized this consumer's source readiness"
COMMANDED = "READY_WITH_LIMITATIONS"  # CP-0 writes T8 exact_command "Run CP-8"
NOT_COMMANDED = "BLOCKED"  # o2's frozen judgement: CP-0 writes "DO NOT RUN"
# opus-medium bills 4 USD per million input and 20 per million output tokens; o2's test usage is
# 1000 input and 200 output tokens: 0.004 + 0.004 for the one CP-0 call.
CP0_CALL_USD = Decimal("0.008")


class _CutReview(o2_case.ScriptAdapter):
    """The frozen o2 readiness review for a CP-0 -> CP-8 plan: one consumer, CP-8, judged
    ``readiness``. A runnable CP-8 borrows CP-6's located evidence and drops the CP-8 gap."""

    readiness = NOT_COMMANDED

    def _plan(self, step_id: str, reads: list[str]) -> list[tuple[str, dict[str, Any]]]:
        plan = super()._plan(step_id, reads)
        if step_id == "source_readiness":
            name, arguments = plan[-1]
            blocked = self.readiness == NOT_COMMANDED
            donor = "CP-8" if blocked else "CP-6"
            entry = next(c for c in arguments["consumers"] if c["module_id"] == donor)
            arguments = {
                **arguments,
                "pack_sha256": Execution(self._execution).read().pack_sha256,
                "consumers": [{**entry, "module_id": "CP-8", "readiness": self.readiness}],
                "gaps": [
                    g for g in arguments["gaps"] if blocked or g["gap_id"] != "missing-prior-record"
                ],
            }
            plan[-1] = (name, load_arguments(json.dumps(arguments)))
        return plan


def _checked(root: Path) -> tuple[CheckedRun, Path]:
    (root / "check").mkdir(parents=True)
    run_dir = root / "run"
    checked = check_arguments(
        case_id=o2_case.CASE_ID,
        sources=o2_case.case_sources(),
        context=o2_case.CASE / "context.json",
        pathway=o2_case.PATHWAY,
        model=o2_case.MODEL,
        adapter=recorded_adapter(o2_case.MODEL, root / "check"),
        cap_usd=o2_case.CAP,
        run_dir=run_dir,
        run_id=o2_case.RUN_ID,
    )
    run = checked.request.run.model_copy(update={"requested_modules": ("CP-0", "CP-8")})
    cut = PreparationRequest(run=run, sources=checked.request.sources)
    return replace(checked, request=cut), run_dir


def _walk(root: Path, readiness: str) -> tuple[RunOutcome, Path]:
    checked, run_dir = _checked(root)
    stage_sources(checked, run_dir)
    (root / "recordings").mkdir()
    script = _CutReview(
        root / "recordings", ("source_readiness",), run_dir / "execution", o2_case.MODEL
    )
    script.readiness = readiness
    return rp._run_pathway(checked, run_dir, script, o2_case.test_prompt_for), run_dir


def _records(run_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (run_dir / "calls.jsonl").read_text().splitlines()]


def _tree(run_dir: Path) -> dict[str, str]:
    return {
        str(p.relative_to(run_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(run_dir.rglob("*"))
        if p.is_file()
    }


def _receipt(run_dir: Path) -> OwnerRunReceipt:
    return OwnerRunReceipt.model_validate_json((run_dir / "owner-run.json").read_text())


def _submit_codes(run_dir: Path) -> list[str | None]:
    return [c["refusal_code"] for r in _records(run_dir) for c in r["tool_calls"]]


def _resume(root: Path, run_dir: Path) -> RunOutcome:
    """Reopen the run with the same arguments and adapter (``resume=True``), as a resume after a
    kill does past ``_resume_pathway``'s read-only checks."""
    checked, _ = _checked(root / "again")
    script = _CutReview(
        root / "recordings", ("source_readiness",), run_dir / "execution", o2_case.MODEL
    )
    return rp._run_pathway(checked, run_dir, script, o2_case.test_prompt_for, resume=True)


class _Kill(BaseException):
    """A process kill: no ``except Exception`` in the run catches it."""


def test_a_commanded_cp8_is_refused_as_superseded_and_the_run_finishes(tmp_path: Path) -> None:
    outcome, run_dir = _walk(tmp_path, COMMANDED)
    snapshot = Execution(run_dir / "execution").read()
    cp0 = next(h for h in snapshot.heads if h.module_id == "CP-0")
    assert [(c.row_id, c.text) for c in cp0.commands] == [("CP-8", "Run CP-8")]  # the premise
    # The walk ends; the receipt is written and verifies; the render stops at the scope check, as
    # the DO-NOT-RUN walk below does (no delivery scope matches the cut CP-0 -> CP-8 plan).
    assert (outcome.outcome, outcome.stopped_reason) == ("stopped", "render: owner_render_scope")
    body = json.loads((run_dir / "run.json").read_text())
    assert (body["outcome"], body["stopped_reason"]) == ("stopped", "render: owner_render_scope")
    receipt = _receipt(run_dir)
    verify_owner_run_receipt(Execution(run_dir / "execution"), receipt, publication_directory=None)
    # No later begin and no publication: the refusal sits on the final snapshot, lacking nothing.
    assert [r.model_dump() for r in receipt.refusals] == [
        {"module_id": "CP-8", "snapshot_sha256": receipt.snapshot_sha256, "reason": SUPERSEDED}
    ]
    assert [b.module_id for b in receipt.begins] == ["CP-0"]
    assert [h.module_id for h in receipt.heads] == ["CP-0"] and receipt.model is None
    assert [(a.module_id, a.status) for a in snapshot.attempts] == [("CP-0", "finished")]
    audit = run_dir / "execution" / AUDIT
    assert len(list((audit / "begins").iterdir())) == 1  # CP-0's; no CP-8 begin
    assert len(list((audit / "refused-begin").iterdir())) == 1
    # One model call, CP-0's; its submit outcome names the first refusal `<module>_<kind>`.
    assert [r["step_id"] for r in _records(run_dir)] == ["source_readiness"]
    assert _submit_codes(run_dir) == ["cp8_superseded"]
    assert outcome.spent_usd == CP0_CALL_USD
    assert not (run_dir / "delivery").exists()


def test_control_the_base_workflow_sends_the_decision_ledger_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same walk on the plain owner workflow begins CP-8 and asks the model for the
    post-mortem: the request the guard removes."""
    monkeypatch.setattr(rp, "_NativeWorkflow", OwnerWorkflow)
    outcome, run_dir = _walk(tmp_path, COMMANDED)
    snapshot = Execution(run_dir / "execution").read()
    assert ("CP-8", "pending") in [(a.module_id, a.status) for a in snapshot.attempts]
    assert [r["step_id"] for r in _records(run_dir)] == ["source_readiness", "decision_ledger"]
    assert outcome.spent_usd > CP0_CALL_USD


def test_a_do_not_run_cp8_keeps_its_retained_refusal_and_the_run_finishes(
    tmp_path: Path,
) -> None:
    """CP-0 assesses every planned consumer, so it always writes a CP-8 command row; o2's frozen
    BLOCKED judgement writes ``DO NOT RUN``. That CP-8 never begins: the walk ends, the receipt
    is written and verifies, and the run stops at the renderer as o2's full walk does."""
    outcome, run_dir = _walk(tmp_path, NOT_COMMANDED)
    heads = Execution(run_dir / "execution").read().heads
    cp0 = next(h for h in heads if h.module_id == "CP-0")
    assert [(c.row_id, c.text) for c in cp0.commands] == [("CP-8", "DO NOT RUN")]
    assert (outcome.outcome, outcome.stopped_reason) == ("stopped", "render: owner_render_scope")
    receipt = OwnerRunReceipt.model_validate_json((run_dir / "owner-run.json").read_text())
    verify_owner_run_receipt(Execution(run_dir / "execution"), receipt, publication_directory=None)
    assert [(r.module_id, r.reason, r.missing_commands) for r in receipt.refusals] == [
        ("CP-8", NOT_AUTHORIZED, ("Run CP-8",))
    ]
    assert [h.module_id for h in receipt.heads] == ["CP-0"]
    assert [r["step_id"] for r in _records(run_dir)] == ["source_readiness"]
    assert _submit_codes(run_dir) == ["cp8_not_authorized"]
    assert outcome.spent_usd == CP0_CALL_USD and not (run_dir / "delivery").exists()


def test_reopening_the_finished_run_writes_nothing_and_a_resume_is_refused(
    tmp_path: Path,
) -> None:
    """The finished run is sealed: ``open`` rebuilds it complete (the superseded refusal and its
    kind included) and writes nothing; a resume is refused because ``run.json`` exists."""
    _, run_dir = _walk(tmp_path, COMMANDED)
    before = _tree(run_dir)
    reopened = rp._NativeWorkflow.open(run_dir / "execution", publication_directory=None)
    assert reopened.phase == "complete"
    assert reopened.state().refusals == _receipt(run_dir).refusals
    assert reopened._refusal_code() == "cp8_superseded"
    checked, _ = _checked(tmp_path / "again")
    with pytest.raises(rp.ResumeRefused, match="already holds run.json"):
        rp._resume_pathway(checked, run_dir, checked.adapter, (), rp.Redactor())
    assert _tree(run_dir) == before


def test_a_run_killed_before_its_receipt_resumes_to_the_same_finish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Killed after the walk retained CP-8's refusal and before the receipt: the resume continues
    past the refusal (no CP-8 begin, no model call) to the receipt and the same render stop."""

    def killed(*_: object) -> None:
        raise _Kill

    with monkeypatch.context() as patched:
        patched.setattr(rp, "_finish_run", killed)
        with pytest.raises(_Kill):
            _walk(tmp_path, COMMANDED)
    run_dir = tmp_path / "run"
    assert not (run_dir / "owner-run.json").exists() and not (run_dir / "run.json").exists()
    outcome = _resume(tmp_path, run_dir)
    assert (outcome.outcome, outcome.stopped_reason) == ("stopped", "render: owner_render_scope")
    assert outcome.spent_usd == CP0_CALL_USD
    receipt = _receipt(run_dir)
    verify_owner_run_receipt(Execution(run_dir / "execution"), receipt, publication_directory=None)
    assert [(r.module_id, r.reason) for r in receipt.refusals] == [("CP-8", SUPERSEDED)]
    assert [r["step_id"] for r in _records(run_dir)] == ["source_readiness"]


def test_a_resumed_run_that_recorded_the_earlier_cp8_stop_keeps_that_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run of the earlier build raised the typed refusal inside CP-0's submit; the loop wrote
    that stop into the call's record. Killed before ``run.json``, its resume stops with the stop the
    record shows (R16): no receipt, no CP-8 attempt or request, CP-0's spend only. ``open`` has
    by then continued the walk, so CP-8's superseded refusal is retained as evidence."""

    def earlier_guard(self: OwnerWorkflow, module_id: str) -> bool:
        if module_id == "CP-8":
            try:
                current_inputs(self._store.read(), module_id)
            except ValueError:
                pass
            else:
                raise rp.NativeCp8Refused
        return OwnerWorkflow._begin(self, module_id)

    with monkeypatch.context() as patched:
        patched.setattr(rp._NativeWorkflow, "_begin", earlier_guard)
        earlier, run_dir = _walk(tmp_path, COMMANDED)
    stop = f"WorkflowError: NativeCp8Refused: {REFUSAL}"
    assert (earlier.outcome, earlier.stopped_reason) == ("stopped", stop)
    (run_dir / "run.json").unlink()  # the kill before run.json
    outcome = _resume(tmp_path, run_dir)
    assert (outcome.outcome, outcome.stopped_reason) == ("stopped", stop)
    assert outcome.spent_usd == CP0_CALL_USD
    assert not (run_dir / "owner-run.json").exists()
    snapshot = Execution(run_dir / "execution").read()
    assert [(a.module_id, a.status) for a in snapshot.attempts] == [("CP-0", "finished")]
    assert [r["step_id"] for r in _records(run_dir)] == ["source_readiness"]
    retained = list((run_dir / "execution" / AUDIT / "refused-begin").iterdir())
    assert [json.loads(p.read_text())["reason"] for p in retained] == [SUPERSEDED]


def test_a_cp8_attempt_an_earlier_run_left_pending_is_not_resumed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with monkeypatch.context() as patched:  # an unguarded run leaves CP-8 pending
        patched.setattr(rp, "_NativeWorkflow", OwnerWorkflow)
        _, run_dir = _walk(tmp_path, COMMANDED)
    before = _tree(run_dir)
    with pytest.raises(rp.NativeCp8Refused):
        rp._NativeWorkflow.open(run_dir / "execution", publication_directory=None)
    # A begun CP-8 cannot be a refused begin: the resumed run stays refused, writing nothing.
    checked, _ = _checked(tmp_path / "again")
    fault = rp._opened(checked, run_dir, load_pack(run_dir / "pack"), True, rp.Redactor())
    assert isinstance(fault, rp._Fault) and fault.reason == f"workflow: {REFUSAL}"
    assert _tree(run_dir) == before
    control = OwnerWorkflow.open(run_dir / "execution", publication_directory=None)
    assert (control.binding.module_id, control.binding.step_id) == ("CP-8", "decision_ledger")


@pytest.mark.parametrize("module", ["CP-0", "CP-1", "CP-3", "CP-5", "CP-6", "CP-L10"])
def test_other_modules_go_straight_to_the_base_begin(
    monkeypatch: pytest.MonkeyPatch, module: str
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(OwnerWorkflow, "_begin", lambda self, m: calls.append(m) or True)
    workflow = object.__new__(rp._NativeWorkflow)
    workflow._store = SimpleNamespace(read=None)  # type: ignore[attr-defined]  # never read
    assert workflow._begin(module) is True
    assert calls == [module]


def test_a_cp8_repair_an_earlier_run_left_next_is_not_begun(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``open`` begins the repair of an attempt 0 settled invalid; a CP-8 attempt already exists,
    so it cannot be recorded as a refused begin and the typed refusal stops the reopening."""
    monkeypatch.setattr(OwnerWorkflow, "_begin", lambda self, m: pytest.fail("base begin"))
    workflow = object.__new__(rp._NativeWorkflow)
    earlier = SimpleNamespace(attempts=(SimpleNamespace(module_id="CP-8"),))
    workflow._store = SimpleNamespace(read=lambda: earlier)  # type: ignore[attr-defined]
    with pytest.raises(rp.NativeCp8Refused):
        workflow._begin("CP-8")


def test_the_typed_refusal_is_a_named_fault_with_the_superseded_reason() -> None:
    assert isinstance(rp.NativeCp8Refused(), rp._FAULTS)
    assert rp.NativeCp8Refused().code == REFUSAL


def _forged(run_dir: Path, refusal: RefusedBegin) -> OwnerRunReceipt:
    """The finished run's receipt with its one refusal replaced, the retained record and the seal
    rewritten to match, so that only the verifier's check of the refusal itself can catch it."""
    receipt = _receipt(run_dir)
    (genuine,) = receipt.refusals
    audit = run_dir / "execution" / AUDIT
    (audit / "refused-begin" / genuine.content_hash()).unlink()
    (audit / "refused-begin" / refusal.content_hash()).write_text(refusal.model_dump_json())
    forged = receipt.model_copy(update={"refusals": (refusal,)})
    (audit / "receipt.sha256").write_text(forged.content_hash())
    return forged


def _with(**fields: Any) -> Callable[[RefusedBegin], RefusedBegin]:
    return lambda genuine: genuine.model_copy(update=fields)


def test_the_forging_harness_keeps_a_genuine_receipt_verifying(tmp_path: Path) -> None:
    _, run_dir = _walk(tmp_path, COMMANDED)
    forged = _forged(run_dir, _receipt(run_dir).refusals[0])
    verify_owner_run_receipt(Execution(run_dir / "execution"), forged, publication_directory=None)


@pytest.mark.parametrize(
    "tamper",
    [
        _with(reason=REFUSAL),  # the typed stop's text, not the refusal's
        _with(reason=SUPERSEDED[:-1]),
        _with(reason=SUPERSEDED + " "),
        _with(reason=NOT_AUTHORIZED, missing_commands=("Run CP-8",)),  # CP-0 did command it
        _with(missing_commands=("Run CP-8",)),
        _with(missing_inputs=("CP-0",)),
    ],
    ids=["typed-text", "truncated", "padded", "not-authorized", "commands", "inputs"],
)
def test_a_tampered_superseded_refusal_fails_verification(
    tmp_path: Path, tamper: Callable[[RefusedBegin], RefusedBegin]
) -> None:
    _, run_dir = _walk(tmp_path, COMMANDED)
    forged = _forged(run_dir, tamper(_receipt(run_dir).refusals[0]))
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        verify_owner_run_receipt(
            Execution(run_dir / "execution"), forged, publication_directory=None
        )


def test_a_superseded_refusal_where_cp0_said_do_not_run_fails_verification(
    tmp_path: Path,
) -> None:
    """The superseded refusal is accepted only where the journal would have begun CP-8."""
    _, run_dir = _walk(tmp_path, NOT_COMMANDED)
    genuine = _receipt(run_dir).refusals[0]
    superseded = RefusedBegin(
        module_id="CP-8", snapshot_sha256=genuine.snapshot_sha256, reason=SUPERSEDED
    )
    forged = _forged(run_dir, superseded)
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        verify_owner_run_receipt(
            Execution(run_dir / "execution"), forged, publication_directory=None
        )


def test_fresh_and_resumed_native_runs_both_use_the_guarded_workflow(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    made: list[type] = []
    monkeypatch.setattr(
        OwnerWorkflow, "create", classmethod(lambda cls, *a, **k: made.append(cls) or cls)
    )
    monkeypatch.setattr(
        OwnerWorkflow, "open", classmethod(lambda cls, *a, **k: made.append(cls) or cls)
    )
    rp._enter(tmp_path, None, False)  # type: ignore[arg-type]
    rp._enter(tmp_path, None, True)  # type: ignore[arg-type]
    assert made == [rp._NativeWorkflow, rp._NativeWorkflow]


def test_the_registered_spec_and_the_comparison_route_stay_separate() -> None:
    from deploy_workflow.owners import cpos

    assert OWNER_SPECS["CP-8"].steps[0].step_id == "decision_ledger"  # kept for old receipts
    assert callable(cpos.run_comparison)
    assert "_NativeWorkflow" not in vars(cpos) and "OwnerWorkflow" not in vars(cpos)


@pytest.mark.parametrize("module", ["CP-0", "CP-1", "CP-6", "CP-MODEL"])
def test_the_superseded_reason_cannot_refuse_any_other_module(tmp_path: Path, module: str) -> None:
    """At the snapshot where CP-8 would begin, CP-0's inputs hold (it needs no command) and every
    module outside the cut plan is not selected: the superseded text is accepted for CP-8 alone."""
    _, run_dir = _walk(tmp_path, COMMANDED)
    store = Execution(run_dir / "execution")
    before = store.read()
    genuine = RefusedBegin(
        module_id="CP-8", snapshot_sha256=before.content_hash(), reason=SUPERSEDED
    )
    _verify_refusal(before, genuine, set())  # the one accepted shape
    for forged in (
        genuine.model_copy(update={"module_id": module}),
        genuine.model_copy(update={"module_id": module, "reason": NOT_AUTHORIZED}),
    ):
        with pytest.raises(WorkflowError, match="identity_mismatch"):
            _verify_refusal(before, forged, set())


def test_a_superseded_refusal_on_an_earlier_snapshot_fails_verification(tmp_path: Path) -> None:
    """The refusal names the snapshot the journal would have begun on (the final one here); the
    empty snapshot before CP-0's begin is a snapshot where CP-8 is not even selected as ready."""
    _, run_dir = _walk(tmp_path, COMMANDED)
    receipt = _receipt(run_dir)
    earlier = receipt.begins[0].snapshot_before_sha256
    assert earlier != receipt.snapshot_sha256
    forged = _forged(
        run_dir,
        RefusedBegin(module_id="CP-8", snapshot_sha256=earlier, reason=SUPERSEDED),
    )
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        verify_owner_run_receipt(
            Execution(run_dir / "execution"), forged, publication_directory=None
        )


def test_a_receipt_with_a_superseded_refusal_and_a_cp8_attempt_fails_the_walk(
    tmp_path: Path,
) -> None:
    """Refused xor settled: a journal that holds a CP-8 attempt cannot also carry CP-8's refusal."""
    from deploy_workflow import owner_workflow as ow

    _, run_dir = _walk(tmp_path, COMMANDED)
    store = Execution(run_dir / "execution")
    receipt = _receipt(run_dir)
    ow._verify_walk(store, receipt, ("CP-0", "CP-8"), ("CP-0", "CP-8"), None)  # the genuine walk
    store.begin("CP-8")  # a CP-8 attempt now exists next to the refusal
    final = store.read().content_hash()
    (refusal,) = receipt.refusals
    both = receipt.model_copy(
        update={
            "snapshot_sha256": final,
            "refusals": (refusal.model_copy(update={"snapshot_sha256": final}),),
        }
    )
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        ow._verify_walk(store, both, ("CP-0", "CP-8"), ("CP-0", "CP-8"), None)
