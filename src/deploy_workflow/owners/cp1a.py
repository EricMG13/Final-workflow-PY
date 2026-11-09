"""CP-1A owner extras: the verifier probe, the one-step probe CP-2 shares and the one-step
submit CP-1B, CP-1C and CP-1D share."""

from collections.abc import Callable
from dataclasses import dataclass

from deploy_vii.business_context import (
    BusinessContextReport,
    _validate_step,
    cp1a_module,
)
from deploy_vii.contracts import Module
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Qualification,
    StepValidation,
    settle,
    text_sha256,
)
from deploy_vii.preparation import PreparedPack
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.workflow import WorkflowError


def probe_one_step(
    store: Execution,
    snapshot: ExecutionSnapshot,
    attempt: Attempt,
    *,
    validate: Callable[[Execution, PreparedPack, Attempt], StepValidation],
    build: Callable[[str, Attempt], Module],
) -> None:
    """Rerun a one-step module's public validator and settlement over the settled snapshot.

    The attempt has exactly one valid step; the module's own `_validate_step`, run on a frozen
    view, gives no issue and the retained output bytes; the rebuilt candidate settles back to
    exactly the finished attempt and the head's module. Nothing is written."""
    if len(attempt.steps) != 1 or attempt.steps[0].status != "valid":
        raise WorkflowError("identity_mismatch")
    step = attempt.steps[0]
    pack = store.pack(snapshot)
    outcome = validate(_FrozenExecution(store, snapshot), pack, attempt)
    if (
        outcome.issues
        or outcome.output is None
        or not outcome.retained_as(step)
        or store.step_output(step.output_sha256 or "") != outcome.output
    ):
        raise WorkflowError("identity_mismatch")
    candidate = build(outcome.output, attempt)
    finished, result = settle(
        snapshot,
        attempt,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("Candidate differs",),
        pack=pack,
        load=store.head_module,
    )
    head = next(h for h in snapshot.heads if h.module_id == attempt.module_id)
    if finished != attempt or result != store.head_module(head):
        raise WorkflowError("identity_mismatch")


@dataclass(frozen=True)
class OneStep:
    """A one-step module as its `submit` settles it: the module's own `_validate_step` (the
    trusted recomputation), its candidate builder and the qualification its head records."""

    module_id: str
    step_id: str
    validate: Callable[[Execution, PreparedPack, Attempt], StepValidation]
    build: Callable[[str, Attempt], Module]
    qualification: Qualification | None


def _retained_valid(attempt: Attempt, module_id: str) -> bool:
    return (
        attempt.module_id == module_id
        and attempt.status == "pending"
        and len(attempt.steps) == 1
        and attempt.steps[0].status == "valid"
    )


def submit_one_step(
    store: Execution,
    ticket_id: str,
    module: OneStep,
    payload: str,
    validate: Callable[[PreparedPack, Attempt], StepValidation],
) -> Attempt:
    """Journal the one step (`validate`, the submit-time validator) and, when it is valid,
    settle the attempt with the Python candidate.

    A crash between the valid step and `finish` resumes, as `submit_cp0_review` does: the same
    payload again finds the retained valid step, skips `submit_step` and settles it, the output
    recomputed by `module.validate` rather than trusted. A different payload is refused."""
    found = next((a for a in store.read().attempts if a.ticket_id == ticket_id), None)
    if found is not None and _retained_valid(found, module.module_id):
        if found.steps[0].payload_sha256 != text_sha256(payload):
            raise ValueError("Ticket already retains a different response; resume or interrupt")
        attempt = found
    else:
        sequence = (module.step_id,)
        attempt = store.submit_step(
            ticket_id, module.module_id, sequence, module.step_id, payload, validate
        )
        if not _retained_valid(attempt, module.module_id):
            return attempt
    outcome = module.validate(store, store.pack(), attempt)
    if outcome.issues or not outcome.retained_as(attempt.steps[0]):
        raise ValueError(f"Retained {module.module_id} output differs from trusted validation")
    candidate = module.build(outcome.output or "", attempt)
    differs = (f"{module.module_id} candidate differs",)
    return store.finish(
        ticket_id,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else differs,
        qualification=module.qualification,
    )


def _candidate(output: str, attempt: Attempt) -> Module:
    report = BusinessContextReport.model_validate_json(output)
    return cp1a_module(report, attempt.inputs, attempt.number)


# The validator the module's own entry hands `Execution.submit_step` (R4-2: the verifier replays
# an invalid step through it at the historical snapshot).
ENTRY_VALIDATOR = _validate_step


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)
