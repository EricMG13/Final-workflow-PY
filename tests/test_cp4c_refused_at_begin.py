"""User ruling: a CP-1 facility issue that no CP-4C response can repair is refused at CP-4C's
begin, before any model call, and the walk continues.

When CP-0 authorizes CP-4C (its `current_inputs` check passes) and CP-1's settled head yields a
CP-4C facility issue (zero or several SECURED T4.18 facilities at the quarter, an alias that
disagrees, no T4.14 period, no single current period, a secured row without its id), the owner
workflow retains `RefusedBegin(CP-4C, <snapshot>, <the issue text>)`: no CP-4C attempt, no model
request, no spend. CP-4C's consumers then see a refused upstream as for any refused module. The
submit outcome names it `cp4c_upstream_fault`. A head with exactly one SECURED facility begins
CP-4C as before; a DO-NOT-RUN or blocked CP-4C keeps its ordinary refusal.

Scope: offline and synthetic. The stores are real `Execution` stores whose CP-0, CP-1, CP-2A and
CP-4 heads are settled through `begin`/`finish` from the CP-4C oracle's records (as
`test_connect_cp4c.seed`; no CP-1 promotion); CP-2G is then begun and submitted through the owner
API (`read_inputs`, `submit_review` with the frozen CP-2G gap literal), and that submit's walk
reaches CP-4C. A sealed `verify_owner_run_receipt` needs every attempt begun through the owner API,
CP-1's promotion included (minutes), so the verifier's walk and refusal checks (`_verify_walk`,
`_verify_refusal`) are run on these journals instead, and a resume is `open()`'s rebuild and
continue steps (`_rebuild_lists`, `_continue_walk`) without its whole-chain reconciliation. A
begun CP-4C step is recorded rather than given its source session (`activations`): that session
checks CP-1's retained promotion chain, which these journals do not hold. No provider is called.
Every expected line is written out by hand from the rows each test writes (as
`tests/test_cp4c_secured_facility.py`).
"""

import importlib
import json
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii.contracts import Fact
from deploy_vii.execution import Execution, plan
from deploy_vii.preparation import PreparedPack
from deploy_workflow import owner_workflow as ow
from deploy_workflow.owner_workflow import AUDIT, OwnerWorkflow, RefusedBegin
from deploy_workflow.workflow import WorkflowError

conn: Any = importlib.import_module("test_connect_cp4c")
stage1: Any = importlib.import_module("test_method_cp4c")
cp2g_stage1: Any = importlib.import_module("test_method_cp2g")

# Written out here, never read from production constants.
BLOCKED = "Required upstream is unrun, stale or blocked"
NOT_AUTHORIZED = "CP-0 has not authorized this consumer's source readiness"
SUPERSEDED = (
    "the decision-ledger post-mortem is superseded; compare prior and current deliverables with "
    "CP-OS run_comparison (deploy_workflow.owners.cpos --compare)"
)
ZERO = (
    "CP-4C: CP-1 T4.18 shows 0 secured facilities at q4-2025, not exactly one, so no secured "
    "facility can be selected"
)
TWO = (
    "CP-4C: CP-1 T4.18 shows 2 secured facilities at q4-2025 (term-loan, revolver), not exactly "
    "one, so no secured facility can be selected"
)
WALK = ("CP-0", "CP-1", "CP-2A", "CP-4", "CP-2G", "CP-4C", "CP-5")
Q4 = "q4-2025"


def _row(row: str, facility: str, secured: str) -> tuple[Fact, ...]:
    return tuple(
        conn._text("T4.18", row, field, value, Q4)
        for field, value in (
            ("facility_id", facility),
            ("period_id", Q4),
            ("secured_status", secured),
            ("seniority", "SENIOR"),
        )
    )


# The base CP-1 head (conn.cp1_facts): at q4-2025 term-loan is SECURED and SENIOR, q3-2025 holds
# an UNSECURED row, the fy-2025 alias row is SECURED and SENIOR; T4.14 states q3-2025, q4-2025
# (QUARTER) and fy-2025 (FY), the last two ending 2025-12-31.
_BASE = conn.cp1_facts()
_NO_T414 = tuple(f for f in _BASE if f.table_id != "T4.14")
_NO_Q4 = tuple(f for f in _BASE if not (f.table_id == "T4.18" and f.row_id == "term-loan"))
FAULTS = {
    "zero": (_NO_Q4, ZERO),
    "two": (_BASE + _row("revolver", "revolver", "SECURED"), TWO),
    "alias": (
        conn.cp1_facts(alias=("SECURED", "SUBORDINATED")),
        "CP-4C: term-loan seniority differs between its q4-2025 row and its fy-2025 alias",
    ),
    "alias-term-missing": (
        tuple(f for f in _BASE if f.fact_id != "cp1-T4.18-term-loan-fy-seniority"),
        "CP-4C: term-loan seniority differs between its q4-2025 row and its fy-2025 alias",
    ),
    "no-t414": (_NO_T414, "CP-4C: CP-1 states no T4.14 period"),
    "twin-quarters": (
        _NO_T414
        + conn._t414(
            (
                ("q3-2025", "QUARTER", "2025-09-30"),
                ("q4-2025", "QUARTER", "2025-12-31"),
                ("q4b-2025", "QUARTER", "2025-12-31"),
            )
        ),
        "CP-4C: CP-1 has no single current T4.18 period at 2025-12-31",
    ),
    "no-facility-id": (
        tuple(
            f
            for f in _BASE
            if (f.table_id, f.row_id, f.field) != ("T4.18", "term-loan", "facility_id")
        ),
        "CP-4C: the one secured CP-1 T4.18 row at q4-2025 states no facility id or no terms",
    ),
}


@pytest.fixture(autouse=True)
def activations(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, int]]:
    """The CP-4C steps the workflow activated: the binding a model request would be made for.
    CP-4C's source session checks CP-1's retained promotion chain, which these seeded journals do
    not hold, so a CP-4C activation is recorded here instead of opening that session; every other
    module activates for real."""
    seen: list[tuple[str, str, int]] = []
    activate = OwnerWorkflow._activate

    def recorded(self: OwnerWorkflow, attempt: Any, step_id: str, *, at: Any = None) -> None:
        if attempt.module_id == "CP-4C":
            seen.append((attempt.module_id, step_id, attempt.number))
            return
        activate(self, attempt, step_id, at=at)

    monkeypatch.setattr(OwnerWorkflow, "_activate", recorded)
    return seen


def _command(module_id: str, text: str) -> Fact:
    return conn._command(module_id).model_copy(update={"text": text})


def _store(
    root: Path,
    cp1: tuple[Fact, ...],
    *,
    requested: tuple[str, ...] = ("CP-4C", "CP-5"),
    cp4c_command: str = "Run CP-4C",
    cp2g: bool = False,
) -> Execution:
    """CP-0, CP-1, CP-2A and CP-4 settled from the oracle's records (`cp1` as CP-1's facts); CP-2G
    too when `cp2g` (its oracle facts and T2H.7 table, as `conn.seed`)."""
    base = conn._pack()
    run = base.run.model_copy(update={"requested_modules": requested})
    store = Execution.create(root / "store", PreparedPack(run=run, sources=base.sources))
    commands = tuple(
        _command(m, cp4c_command if m == "CP-4C" else f"Run {m}")
        for m in ("CP-1", "CP-2A", "CP-4", "CP-2G", "CP-4C", "CP-5", "CP-8")
    )
    conn._finish(store, "CP-0", commands, "CP-0 note")
    conn._finish(store, "CP-1", cp1, "CP-1 note")
    conn._finish(store, "CP-2A", conn.oracle_facts(stage1.CP2A_EXP, "positive"), "CP-2A note")
    conn._finish(store, "CP-4", stage1._cp4("positive").facts, "CP-4 note")
    if cp2g:
        body = conn.oracle_facts(stage1.CP2G_EXP, "gap")
        conn._finish(store, "CP-2G", body, "CP-2G note", (conn._t2h7(),))
    return store


def _workflow(store: Execution, kind: type[OwnerWorkflow] = OwnerWorkflow) -> OwnerWorkflow:
    """An owner workflow over the seeded journal, as `create` sets one up (no CP-0 begin)."""
    workflow = object.__new__(kind)
    workflow._setup(store, plan(store.read().run.requested_modules), None)
    return workflow


def _submit_cp2g(workflow: OwnerWorkflow, payload: str | None = None) -> dict[str, Any]:
    """CP-2G's one exact read, then the frozen CP-2G gap literal (figures bound) or `payload`."""
    workflow.read_inputs()
    if payload is None:
        payload = json.dumps(cp2g_stage1._bind_all(cp2g_stage1._payload("gap")))
    outcome: dict[str, Any] = workflow.submit_review(payload)
    return outcome


def _walk(root: Path, cp1: tuple[Fact, ...], **seed: Any) -> tuple[OwnerWorkflow, dict[str, Any]]:
    """Begin CP-2G through the owner workflow and submit it: the walk then reaches CP-4C."""
    workflow = _workflow(_store(root, cp1, **seed))
    assert workflow._begin("CP-2G") is True
    return workflow, _submit_cp2g(workflow)


def _attempts(store: Execution) -> list[tuple[str, str]]:
    return [(a.module_id, a.status) for a in store.read().attempts]


def _audit(store: Execution, kind: str) -> list[dict[str, Any]]:
    directory = store.directory / AUDIT / kind
    paths = sorted(directory.iterdir()) if directory.is_dir() else []
    return [json.loads(p.read_text()) for p in paths]


def _check_walk(workflow: OwnerWorkflow, *, refusals: Any = None) -> None:
    """The verifier's walk check (settled xor refused, each refusal on the snapshot the walk
    expects and recomputed there by `_verify_refusal`) over the workflow's own records."""
    receipt = SimpleNamespace(
        refusals=tuple(workflow._refusals if refusals is None else refusals),
        begins=tuple(workflow._begins),
        publications=(),
    )
    ow._verify_walk(workflow._store, receipt, workflow._analytical, workflow._plan, None)


# --- the ruling: refused at begin, no attempt, the walk goes on ----------------------------------


@pytest.mark.parametrize("fault", list(FAULTS))
def test_a_hopeless_facility_issue_is_refused_at_begin_and_the_walk_continues(
    tmp_path: Path, fault: str, activations: list[tuple[str, str, int]]
) -> None:
    cp1, line = FAULTS[fault]
    workflow, outcome = _walk(tmp_path, cp1)
    store = workflow._store
    final = store.read().content_hash()
    # CP-2G's submit is valid; its walk refused CP-4C with the issue and CP-5 as its consequence.
    assert (outcome["status"], outcome["step_id"]) == ("valid", "forward_credit_model")
    assert outcome["refusal"] == "cp4c_upstream_fault"
    assert outcome["snapshot_sha256"] == final
    assert [r.model_dump() for r in workflow._refusals] == [
        {"module_id": "CP-4C", "snapshot_sha256": final, "reason": line},
        {
            "module_id": "CP-5",
            "snapshot_sha256": final,
            "reason": BLOCKED,
            "missing_inputs": ("CP-4C",),
        },
    ]
    # No CP-4C or CP-5 attempt, begin or step: nothing a model could be asked for, nothing spent.
    assert workflow.phase == "complete" and activations == []
    assert _attempts(store) == [
        ("CP-0", "finished"),
        ("CP-1", "finished"),
        ("CP-2A", "finished"),
        ("CP-4", "finished"),
        ("CP-2G", "finished"),
    ]
    assert [b.module_id for b in workflow._begins] == ["CP-2G"]
    assert [b["module_id"] for b in _audit(store, "begins")] == ["CP-2G"]
    retained = sorted((r["module_id"], r["reason"]) for r in _audit(store, "refused-begin"))
    assert retained == [("CP-4C", line), ("CP-5", BLOCKED)]
    assert [h.module_id for h in store.read().heads] == ["CP-0", "CP-1", "CP-2A", "CP-4", "CP-2G"]
    # The verifier accepts the walk: the refusal recomputes at its snapshot.
    _check_walk(workflow)


def test_the_refusal_names_the_last_planned_module_and_ends_the_walk(tmp_path: Path) -> None:
    """With CP-4C last in the plan the refused begin ends the walk complete."""
    workflow, outcome = _walk(tmp_path, _NO_Q4, requested=("CP-4C",))
    final = workflow._store.read().content_hash()
    assert outcome["refusal"] == "cp4c_upstream_fault"
    assert workflow._refusals == [
        RefusedBegin(module_id="CP-4C", snapshot_sha256=final, reason=ZERO)
    ]
    assert workflow.phase == "complete"
    assert workflow._plan == WALK[:-1]
    _check_walk(workflow)


def test_the_native_pathway_workflow_refuses_the_same_way(tmp_path: Path) -> None:
    """`run_pathway`'s workflow inherits the owner begin for CP-4C (it guards CP-8 only)."""
    from deploy_workflow import run_pathway as rp

    workflow = _workflow(_store(tmp_path, _NO_Q4), rp._NativeWorkflow)
    assert workflow._begin("CP-2G") is True
    outcome = _submit_cp2g(workflow)
    final = workflow._store.read().content_hash()
    assert outcome["refusal"] == "cp4c_upstream_fault" and workflow.phase == "complete"
    assert [(r.module_id, r.reason) for r in workflow._refusals] == [
        ("CP-4C", ZERO),
        ("CP-5", BLOCKED),
    ]
    assert all(r.snapshot_sha256 == final for r in workflow._refusals)
    _check_walk(workflow)


def test_one_secured_facility_begins_cp4c_as_before(
    tmp_path: Path, activations: list[tuple[str, str, int]]
) -> None:
    workflow, outcome = _walk(tmp_path, _BASE)
    store = workflow._store
    assert outcome["status"] == "valid" and outcome["refusal"] is None
    assert workflow._refusals == [] and workflow.phase == "analytical"
    assert activations == [("CP-4C", "restructuring_fulcrum", 0)]
    assert _attempts(store)[-1] == ("CP-4C", "pending")
    assert [b.module_id for b in workflow._begins] == ["CP-2G", "CP-4C"]
    assert ow._upstream_fault(store, store.read(), "CP-4C") is None


def test_a_do_not_run_cp4c_keeps_its_not_authorized_refusal(tmp_path: Path) -> None:
    """CP-0 does not authorize CP-4C: the facility issue is never read; the ordinary refusal."""
    workflow, outcome = _walk(tmp_path, _NO_Q4, cp4c_command="DO NOT RUN")
    final = workflow._store.read().content_hash()
    assert outcome["refusal"] == "cp4c_not_authorized"
    assert [r.model_dump() for r in workflow._refusals] == [
        {
            "module_id": "CP-4C",
            "snapshot_sha256": final,
            "reason": NOT_AUTHORIZED,
            "missing_commands": ("Run CP-4C",),
        },
        {
            "module_id": "CP-5",
            "snapshot_sha256": final,
            "reason": BLOCKED,
            "missing_inputs": ("CP-4C",),
        },
    ]
    _check_walk(workflow)
    # The upstream-fault shape is not accepted where CP-0 said DO NOT RUN.
    forged = RefusedBegin(module_id="CP-4C", snapshot_sha256=final, reason=ZERO)
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        _check_walk(workflow, refusals=(forged, workflow._refusals[1]))


def test_a_blocked_cp2g_keeps_cp4c_blocked_refusal_over_a_cp1_fault(tmp_path: Path) -> None:
    """CP-2G settles blocked (two invalid submissions): CP-4C's begin is the blocked edge."""
    workflow = _workflow(_store(tmp_path, _NO_Q4))
    assert workflow._begin("CP-2G") is True
    assert _submit_cp2g(workflow, "{}")["status"] == "invalid"
    outcome = _submit_cp2g(workflow, "{}")
    final = workflow._store.read().content_hash()
    assert (outcome["status"], outcome["refusal"]) == ("invalid", "cp4c_blocked")
    assert [r.model_dump() for r in workflow._refusals] == [
        {
            "module_id": "CP-4C",
            "snapshot_sha256": final,
            "reason": BLOCKED,
            "missing_inputs": ("CP-2G",),
        },
        # CP-5's edge to CP-2G is restricted: the blocked CP-2G head is bound, CP-4C is missing.
        {
            "module_id": "CP-5",
            "snapshot_sha256": final,
            "reason": BLOCKED,
            "missing_inputs": ("CP-4C",),
        },
    ]
    _check_walk(workflow)


def test_a_repair_an_earlier_run_left_next_is_begun_as_before(
    tmp_path: Path, activations: list[tuple[str, str, int]]
) -> None:
    """An earlier build began CP-4C over the fault and it settled rejected: a CP-4C attempt
    exists, so the journal's own repair begins (a refusal beside an attempt cannot verify)."""
    store = _store(tmp_path, _NO_Q4, requested=("CP-4C",), cp2g=True)
    first = store.begin("CP-4C")
    conn._submit(store, first, json.dumps(conn._payload("positive")))
    assert conn._finished(store, first).issues == (ZERO,)
    before = store.read()
    assert ow._upstream_fault(store, before, "CP-4C") is None
    workflow = _workflow(store)
    assert workflow._begin("CP-4C") is True
    assert workflow._refusals == [] and activations == [("CP-4C", "restructuring_fulcrum", 1)]
    repair = store.read().attempts[-1]
    assert (repair.module_id, repair.number, repair.repair_issues) == ("CP-4C", 1, (ZERO,))
    forged = RefusedBegin(module_id="CP-4C", snapshot_sha256=before.content_hash(), reason=ZERO)
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        ow._verify_refusal(before, forged, set(), ow._upstream_fault(store, before, "CP-4C"))


def test_no_refusal_is_read_while_another_attempt_is_pending(tmp_path: Path) -> None:
    """`Execution.begin` refuses every begin while an attempt is pending: the journal would not
    begin CP-4C there, so no upstream-fault refusal is read or accepted (CP-8 needs only CP-0)."""
    store = _store(tmp_path, _NO_Q4, requested=("CP-4C", "CP-8"), cp2g=True)
    assert ow._upstream_fault(store, store.read(), "CP-4C") == ZERO  # the premise
    store.begin("CP-8")
    before = store.read()
    assert ow._upstream_fault(store, before, "CP-4C") is None
    forged = RefusedBegin(module_id="CP-4C", snapshot_sha256=before.content_hash(), reason=ZERO)
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        ow._verify_refusal(before, forged, set(), ow._upstream_fault(store, before, "CP-4C"))


# --- the verifier: the refusal is accepted only as the journal recomputes it ---------------------


def _replace(field: str, value: Any) -> Callable[[RefusedBegin], RefusedBegin]:
    return lambda genuine: genuine.model_copy(update={field: value})


@pytest.mark.parametrize(
    "tamper",
    [
        _replace("reason", TWO),  # another facility issue than the head's
        _replace("reason", ZERO + " "),
        _replace("reason", ZERO[:-1]),
        _replace("reason", "CP-1 upstream fault: " + ZERO),
        _replace("reason", BLOCKED),
        _replace("reason", SUPERSEDED),
        _replace("missing_inputs", ("CP-1",)),
        _replace("missing_commands", ("Run CP-4C",)),
        _replace("module_id", "CP-2G"),  # a settled module
    ],
    ids=[
        "other-issue",
        "padded",
        "truncated",
        "prefixed",
        "blocked-text",
        "superseded-text",
        "inputs",
        "commands",
        "other-module",
    ],
)
def test_a_tampered_upstream_fault_refusal_fails_verification(
    tmp_path: Path, tamper: Callable[[RefusedBegin], RefusedBegin]
) -> None:
    workflow, _ = _walk(tmp_path, _NO_Q4)
    genuine, consequence = workflow._refusals
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        _check_walk(workflow, refusals=(tamper(genuine), consequence))


def test_the_fault_text_cannot_refuse_another_module(tmp_path: Path) -> None:
    """CP-5's consequence refusal rewritten to the facility issue, lacking nothing."""
    workflow, _ = _walk(tmp_path, _NO_Q4)
    genuine, consequence = workflow._refusals
    forged = RefusedBegin(
        module_id="CP-5", snapshot_sha256=consequence.snapshot_sha256, reason=ZERO
    )
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        _check_walk(workflow, refusals=(genuine, forged))
    before = ow._snapshot(workflow._store, genuine.snapshot_sha256)
    for module_id in ("CP-0", "CP-1", "CP-2G", "CP-5", "CP-8"):
        moved = genuine.model_copy(update={"module_id": module_id})
        with pytest.raises(WorkflowError, match="identity_mismatch"):
            ow._verify_refusal(before, moved, {"CP-4C"}, ZERO)


def test_a_refusal_on_another_snapshot_fails_verification(tmp_path: Path) -> None:
    """The snapshot before CP-2G began: CP-4C's inputs do not hold there (CP-2G unrun)."""
    workflow, _ = _walk(tmp_path, _NO_Q4)
    genuine, consequence = workflow._refusals
    earlier = workflow._begins[0].snapshot_before_sha256
    assert earlier != genuine.snapshot_sha256
    moved = genuine.model_copy(update={"snapshot_sha256": earlier})
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        _check_walk(workflow, refusals=(moved, consequence))
    store = workflow._store
    before = ow._snapshot(store, earlier)
    assert ow._upstream_fault(store, before, "CP-4C") is None
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        ow._verify_refusal(before, moved, set(), ZERO)


def test_a_refusal_beside_a_cp4c_attempt_fails_verification(tmp_path: Path) -> None:
    workflow, _ = _walk(tmp_path, _NO_Q4, requested=("CP-4C",))
    store = workflow._store
    _check_walk(workflow)  # the genuine walk
    store.begin("CP-4C")  # a CP-4C attempt now exists next to the refusal
    final = store.read().content_hash()
    (refusal,) = workflow._refusals
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        _check_walk(workflow, refusals=(refusal.model_copy(update={"snapshot_sha256": final}),))


@pytest.mark.parametrize(
    "cp1,claimed",
    [(_BASE, ZERO), (FAULTS["two"][0], ZERO), (_NO_Q4, TWO)],
    ids=["single-facility", "two-claimed-zero", "zero-claimed-two"],
)
def test_a_reason_the_cp1_head_does_not_yield_fails_verification(
    tmp_path: Path, cp1: tuple[Fact, ...], claimed: str
) -> None:
    """CP-2G settled and CP-4C never begun; a refusal claims a facility issue at the final
    snapshot, where the journal would begin CP-4C: only the head's own issue is accepted."""
    store = _store(tmp_path, cp1, requested=("CP-4C",), cp2g=True)
    final = store.read().content_hash()
    forged = RefusedBegin(module_id="CP-4C", snapshot_sha256=final, reason=claimed)
    planned = WALK[:-1]

    def check(refusal: RefusedBegin) -> None:
        receipt = SimpleNamespace(refusals=(refusal,), begins=(), publications=())
        ow._verify_walk(store, receipt, planned, planned, None)

    with pytest.raises(WorkflowError, match="identity_mismatch"):
        check(forged)
    actual = ow._upstream_fault(store, store.read(), "CP-4C")
    if actual is not None:  # the head's own issue is the one accepted shape
        check(forged.model_copy(update={"reason": actual}))


def test_the_kind_is_named_from_the_retained_refusal() -> None:
    zero = "0" * 64
    fault = RefusedBegin(module_id="CP-4C", snapshot_sha256=zero, reason=ZERO)
    assert ow._kind_of(fault) == "upstream_fault"
    blocked = RefusedBegin(
        module_id="CP-4C", snapshot_sha256=zero, reason=BLOCKED, missing_inputs=("CP-2G",)
    )
    assert ow._kind_of(blocked) == "blocked"
    commanded = RefusedBegin(
        module_id="CP-4C",
        snapshot_sha256=zero,
        reason=NOT_AUTHORIZED,
        missing_commands=("Run CP-4C",),
    )
    assert ow._kind_of(commanded) == "not_authorized"
    superseded = RefusedBegin(module_id="CP-8", snapshot_sha256=zero, reason=SUPERSEDED)
    assert ow._kind_of(superseded) == "superseded"
    other = RefusedBegin(module_id="CP-5", snapshot_sha256=zero, reason=BLOCKED)
    assert ow._kind_of(other) == "blocked"


# --- resume -------------------------------------------------------------------------------------


class _Kill(BaseException):
    """A process kill: no `except Exception` in the workflow catches it."""


def test_a_walk_killed_after_the_refusal_resumes_past_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Killed after CP-4C's refusal was retained, before the walk moved on. The resume rebuilds
    the lists from the retained audit (`_rebuild_lists`, open()'s own step; open() itself also
    reconciles the whole chain, which these seeded journals do not retain), names the kind again
    and continues the walk (`_continue_walk`): CP-5 refused, no CP-4C begin, no request."""
    advance = OwnerWorkflow._advance

    def killed(self: OwnerWorkflow, module_id: str) -> None:
        if module_id == "CP-4C":
            raise _Kill
        advance(self, module_id)

    with monkeypatch.context() as patched:
        patched.setattr(OwnerWorkflow, "_advance", killed)
        with pytest.raises(_Kill):
            _walk(tmp_path, _NO_Q4)
    store = Execution(tmp_path / "store")
    final = store.read().content_hash()
    assert [(r["module_id"], r["reason"]) for r in _audit(store, "refused-begin")] == [
        ("CP-4C", ZERO)
    ]
    resumed = _workflow(store)
    chain = ow._chain_of(store)
    position = {s.content_hash(): i for i, s in enumerate(chain)}
    resumed._rebuild_lists(ow._retained_audit(store), position)
    assert resumed._refusal_code() == "cp4c_upstream_fault"  # recomputed from the record
    resumed._continue_walk(chain[-1], None)
    assert resumed.phase == "complete"
    assert [r.model_dump() for r in resumed._refusals] == [
        {"module_id": "CP-4C", "snapshot_sha256": final, "reason": ZERO},
        {
            "module_id": "CP-5",
            "snapshot_sha256": final,
            "reason": BLOCKED,
            "missing_inputs": ("CP-4C",),
        },
    ]
    assert resumed._refusal_code() == "cp4c_upstream_fault"
    assert all(a.module_id != "CP-4C" for a in store.read().attempts)
    assert store.read().content_hash() == final
    assert len(_audit(store, "refused-begin")) == 2
    _check_walk(resumed)


def test_a_walk_killed_before_the_refusal_was_retained_recomputes_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Killed after CP-2G settled and before CP-4C's refusal was retained: the resume continues
    from CP-2G's begin and `_begin` recomputes the same refusal at the same snapshot."""
    retain = ow._retain

    def killed(store: Execution, kind: str, value: Any) -> None:
        if kind == "refused-begin":
            raise _Kill
        retain(store, kind, value)

    with monkeypatch.context() as patched:
        patched.setattr(ow, "_retain", killed)
        with pytest.raises(_Kill):
            _walk(tmp_path, _NO_Q4)
    store = Execution(tmp_path / "store")
    final = store.read().content_hash()
    assert _audit(store, "refused-begin") == []
    resumed = _workflow(store)
    chain = ow._chain_of(store)
    position = {s.content_hash(): i for i, s in enumerate(chain)}
    resumed._rebuild_lists(ow._retained_audit(store), position)
    resumed._continue_walk(chain[-1], None)
    assert resumed.phase == "complete"
    assert resumed._refusal_code() == "cp4c_upstream_fault"
    assert [(r.module_id, r.snapshot_sha256, r.reason) for r in resumed._refusals] == [
        ("CP-4C", final, ZERO),
        ("CP-5", final, BLOCKED),
    ]
    assert all(a.module_id != "CP-4C" for a in store.read().attempts)
    _check_walk(resumed)


# --- review: a head `cp1_of` cannot read, purity, an older build's attempt -----------------------


def _tree(root: Path) -> dict[str, bytes]:
    """Every file under `root` with its bytes: what a read must leave unchanged."""
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


def _verify_refusal_at(store: Execution, refusal: RefusedBegin) -> None:
    before = ow._snapshot(store, refusal.snapshot_sha256)
    ow._verify_refusal(before, refusal, set(), ow._upstream_fault(store, before, refusal.module_id))


def test_a_duplicate_cp1_coordinate_is_not_a_fault_and_cp4c_begins_as_before(
    tmp_path: Path, activations: list[tuple[str, str, int]]
) -> None:
    """Two T4.18 facts at term-loan/seniority: `cp4c._rows` raises ValueError, as it does for a
    begun CP-4C. `_upstream_fault` must not stop the run: no fault, the journal's own begin."""
    twin = next(
        f for f in _BASE if (f.table_id, f.row_id, f.field) == ("T4.18", "term-loan", "seniority")
    )
    duplicate = _BASE + (twin.model_copy(update={"fact_id": twin.fact_id + "-twin"}),)
    store = _store(tmp_path, duplicate, requested=("CP-4C",), cp2g=True)
    before = store.read()
    assert ow._upstream_fault(store, before, "CP-4C") is None
    # A forged refusal naming any text cannot pass either, and fails closed as a WorkflowError.
    for text in (ZERO, "CP-4C: duplicate CP-1 coordinate T4.18/term-loan"):
        forged = RefusedBegin(module_id="CP-4C", snapshot_sha256=before.content_hash(), reason=text)
        with pytest.raises(WorkflowError, match="identity_mismatch"):
            _verify_refusal_at(store, forged)
    workflow = _workflow(store)
    assert workflow._begin("CP-4C") is True and workflow._refusals == []
    assert activations == [("CP-4C", "restructuring_fulcrum", 0)]


def test_an_unreadable_cp1_blob_is_not_a_fault(tmp_path: Path) -> None:
    store = _store(tmp_path, _NO_Q4, requested=("CP-4C",), cp2g=True)
    before = store.read()
    assert ow._upstream_fault(store, before, "CP-4C") == ZERO  # the premise
    cp1 = next(h for h in before.heads if h.module_id == "CP-1")
    (store.directory / "blobs" / cp1.result_sha256).unlink()
    assert ow._upstream_fault(store, before, "CP-4C") is None
    forged = RefusedBegin(module_id="CP-4C", snapshot_sha256=before.content_hash(), reason=ZERO)
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        ow._verify_refusal(before, forged, set(), ow._upstream_fault(store, before, "CP-4C"))


def test_upstream_fault_only_reads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The journal's files are byte-identical after the check, in both its answers; another
    module reads no blob at all."""
    for cp1, expected in ((_NO_Q4, ZERO), (_BASE, None)):
        store = _store(tmp_path / str(expected is None), cp1, requested=("CP-4C",), cp2g=True)
        snapshot = store.read()
        seen = _tree(store.directory)
        assert ow._upstream_fault(store, snapshot, "CP-4C") == expected
        assert ow._upstream_fault(store, snapshot, "CP-4C") == expected
        assert _tree(store.directory) == seen and store.read() == snapshot

    def boom(digest: str) -> None:
        raise AssertionError("a blob was read")

    monkeypatch.setattr(store, "result", boom)
    assert ow._upstream_fault(store, store.read(), "CP-2G") is None


def test_cp4c_is_a_blocking_input_edge_of_cp1_in_every_plan_with_cp4c() -> None:
    """The `next()` in `_upstream_fault`: CP-1 is bound as an input wherever CP-4C is selected."""
    from deploy_vii.execution import dependencies, edge_rule
    from deploy_vii.registry import modules

    every = tuple(m.module_id for m in modules())
    for requested in (("CP-4C",), ("CP-4C", "CP-5"), ("CP-4C", "CP-1C", "CP-3C"), every):
        graph = dependencies(requested)
        assert {"CP-0", "CP-1", "CP-2G", "CP-4", "CP-2A"} <= graph["CP-4C"]
        assert edge_rule("CP-4C", "CP-1") == "block"  # only an accepted or restricted head binds


def test_a_cp4c_attempt_an_older_build_left_pending_is_not_refused(tmp_path: Path) -> None:
    """Begun over the fault by a build without the rule and killed before a response: the
    attempt stands, the fault is not read, and a refusal beside it cannot verify."""
    store = _store(tmp_path, _NO_Q4, requested=("CP-4C",), cp2g=True)
    store.begin("CP-4C")
    before = store.read()
    assert ow._upstream_fault(store, before, "CP-4C") is None
    forged = RefusedBegin(module_id="CP-4C", snapshot_sha256=before.content_hash(), reason=ZERO)
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        _verify_refusal_at(store, forged)
    final = before.content_hash()
    receipt = SimpleNamespace(refusals=(forged,), begins=(), publications=())
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        ow._verify_walk(store, receipt, ("CP-4C",), ("CP-4C",), None)
    assert final == store.read().content_hash()
